"""Reviewed updates for the existing fifth-page adapter. No build or hardware IO."""
import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import uuid
import core
import exporter

ROOT = core.ROOT
STATE = ROOT / 'integration_state.json'
HISTORY = ROOT / 'integration_history'
FILES = tuple('ui_' + stem + ext for stem in ('assets', 'pages', 'actions') for ext in ('.c', '.h'))

def digest(b):
    return hashlib.sha256(b).hexdigest()

def encoded(obj):
    return (json.dumps(obj, ensure_ascii=False, indent=2) + '\n').encode('utf-8')

def atomic(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)

@contextmanager
def locked():
    import msvcrt
    HISTORY.mkdir(parents=True, exist_ok=True)
    with (HISTORY / '.lock').open('a+b') as lock:
        lock.seek(0, 2)
        if not lock.tell(): lock.write(b'0'); lock.flush()
        lock.seek(0)
        msvcrt.locking(lock.fileno(), msvcrt.LK_LOCK, 1)
        try: yield
        finally:
            lock.seek(0)
            msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)

def target(name):
    if name not in FILES: raise ValueError('非界面生成文件')
    p = core.FIRMWARE / 'Hardware' / name
    if p.resolve().parent != (core.FIRMWARE / 'Hardware').resolve():
        raise ValueError('目标文件指向工程外部')
    return p

def snapshot(name):
    for record in HISTORY.glob('*/transaction.json'):
        if json.loads(record.read_text(encoding='utf-8'))['status'] == 'prepared':
            raise ValueError('存在中断的更新，请先 rollback：' + record.parent.name)
    core.draft_path(name)
    folder = exporter.EXPORTS / name
    if folder.resolve().parent != exporter.EXPORTS.resolve():
        raise ValueError('导出目录指向外部')
    design = json.loads((folder / 'ui_design.json').read_text(encoding='utf-8'))
    generated, manifest = exporter.generate(design)  # Rechecks the current adapter.
    # Reject edited C and stale exports, even if their manifest was also edited.
    for fn, content in generated.items():
        if (folder / fn).read_bytes() != content.encode('utf-8'):
            raise ValueError('导出内容与当前生成器不一致，请重新导出：' + fn)
    state_bytes = STATE.read_bytes()
    state = json.loads(state_bytes)
    rows = []
    for fn in FILES:
        old = digest(target(fn).read_bytes())
        if old != state['files'].get(fn):
            raise ValueError('工程生成文件被手工修改，拒绝覆盖：' + fn)
        new = digest(generated[fn].encode('utf-8'))
        rows.append({'file': 'Hardware/' + fn, 'before': old, 'after': new,
                     'status': '修改' if old != new else '不变'})
    blockers = []
    if len(design['pages']) != 1:
        blockers.append('当前第五页接入仅支持一页；多页跳转须先接入实体事件。')
    for pg in design['pages']:
        if any(a.get('type') != 'none' for a in pg['bindings'].values()):
            blockers.append('设计含按键或旋钮动作，当前固件尚未转发 ui_event，需单独接入。')
        if any(e['kind'] == 'dialog' for e in pg['elements']):
            blockers.append('设计含弹窗，需先确认实体按键与退出规则。')
    report = {'export': name, 'state_sha256': digest(state_bytes),
              'design_sha256': manifest['design_sha256'], 'profile': manifest['profile'],
              'changes': rows, 'blockers': list(dict.fromkeys(blockers)),
              'warnings': manifest['warnings'] + ['变量仅使用设计初始值，未绑定真实传感器。'],
              'validation': {'keil_compile': 'not_run', 'hardware': 'not_run'}}
    return report, generated

def review(name):
    """Read-only firmware review; records a plan and a human-readable diff."""
    import difflib
    with locked():
        report, generated = snapshot(name)
        ident = uuid.uuid4().hex
        folder = HISTORY / ident
        folder.mkdir()
        atomic(folder / 'plan.json', encoded(report))
        diff = ''.join(''.join(difflib.unified_diff(
            target(fn).read_text(encoding='utf-8').splitlines(True),
            generated[fn].splitlines(True), fromfile='a/Hardware/' + fn,
            tofile='b/Hardware/' + fn)) for fn in FILES)
        atomic(folder / 'changes.diff', diff.encode('utf-8'))
        return dict(report, plan_id=ident, directory=str(folder.resolve()))

def plan_folder(ident):
    if not re.fullmatch('[0-9a-f]{32}', ident): raise ValueError('无效计划编号')
    p = HISTORY / ident
    if p.resolve().parent != HISTORY.resolve(): raise ValueError('计划目录指向外部')
    return p

def apply(ident):
    """Explicit CLI step only. Never exposed as a webpage or MCP write tool."""
    with locked():
        folder = plan_folder(ident)
        if (folder / 'transaction.json').exists(): raise ValueError('计划已执行，不能重复应用')
        plan = json.loads((folder / 'plan.json').read_text(encoding='utf-8'))
        current, generated = snapshot(plan['export'])
        if current != plan: raise ValueError('导出或工程已变化，请重新审阅')
        if plan['blockers']: raise ValueError('尚有接入阻碍：' + '；'.join(plan['blockers']))
        if all(row['status'] == '不变' for row in plan['changes']):
            return {'status': 'no_changes', 'plan_id': ident}
        previous = STATE.read_bytes()
        for fn in FILES: atomic(folder / 'backup' / fn, target(fn).read_bytes())
        atomic(folder / 'backup' / 'state.json', previous)
        state = json.loads(previous)
        state.update(files={fn: digest(generated[fn].encode('utf-8')) for fn in FILES},
                     design_sha256=plan['design_sha256'], last_plan=ident)
        tx = {'status': 'prepared', 'after_state': digest(encoded(state)),
              'files': state['files'], 'validation': plan['validation']}
        atomic(folder / 'transaction.json', encoded(tx))
        try:
            for fn in FILES: atomic(target(fn), generated[fn].encode('utf-8'))
            atomic(STATE, encoded(state))
        except Exception:
            for fn in FILES: atomic(target(fn), (folder / 'backup' / fn).read_bytes())
            atomic(STATE, previous)
            tx['status'] = 'reverted_after_error'
            atomic(folder / 'transaction.json', encoded(tx))
            raise
        tx['status'] = 'applied'
        atomic(folder / 'transaction.json', encoded(tx))
        return dict(tx, plan_id=ident)

def rollback(ident):
    """Restore only untouched generated files, including interrupted updates."""
    with locked():
        folder = plan_folder(ident)
        tx = json.loads((folder / 'transaction.json').read_text(encoding='utf-8'))
        if tx['status'] not in ('prepared', 'applied'):
            raise ValueError('此计划不可回退')
        before = (folder / 'backup' / 'state.json').read_bytes()
        state = json.loads(before)
        if digest(STATE.read_bytes()) not in (digest(before), tx['after_state']):
            raise ValueError('后续更新已发生，拒绝覆盖；请先回退最近一次更新')
        backups = {}
        for fn in FILES:
            backups[fn] = (folder / 'backup' / fn).read_bytes()
            if digest(backups[fn]) != state['files'][fn]: raise ValueError('备份校验失败：' + fn)
            if digest(target(fn).read_bytes()) not in (state['files'][fn], tx['files'][fn]):
                raise ValueError('文件后来被修改，拒绝回退覆盖：' + fn)
        for fn in FILES: atomic(target(fn), backups[fn])
        atomic(STATE, before)
        tx['status'] = 'rolled_back'
        atomic(folder / 'transaction.json', encoded(tx))
        return dict(tx, plan_id=ident)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='同一 Keil 工程的界面审阅、应用与回退；不编译或烧录')
    parser.add_argument('operation', choices=['review', 'apply', 'rollback'])
    parser.add_argument('name', help='review 使用导出名称；apply/rollback 使用计划编号')
    args = parser.parse_args()
    try:
        print(json.dumps(globals()[args.operation](args.name), ensure_ascii=False, indent=2))
    except (ValueError, OSError, KeyError, RuntimeError) as exc:
        parser.exit(1, str(exc) + '\n')
