"""Local idea inbox. Proposals require explicit application and a matching revision."""
from contextlib import contextmanager
from datetime import datetime, timezone
import copy
import json
import re
import threading
import uuid
import core
import studio
from integration import atomic, encoded

ROOT = core.ROOT / 'requests'
LOCK = threading.RLock()

@contextmanager
def locked():
    import msvcrt
    ROOT.mkdir(parents=True, exist_ok=True)
    with LOCK, (ROOT / '.lock').open('a+b') as lock:
        lock.seek(0, 2)
        if lock.tell() == 0: lock.write(b'0'); lock.flush()
        lock.seek(0); msvcrt.locking(lock.fileno(), msvcrt.LK_LOCK, 1)
        try: yield
        finally:
            lock.seek(0); msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)

def path(ident):
    if not re.fullmatch('[0-9a-f]{32}', ident): raise ValueError('请求编号无效')
    return ROOT / (ident + '.json')

def read(ident):
    return json.loads(path(ident).read_text(encoding='utf-8'))

def write(r):
    r['updated_at'] = datetime.now(timezone.utc).isoformat()
    atomic(path(r['id']), encoded(r))
    return r

def list_requests(name=None):
    if name is not None: core.draft_path(name)
    rows = [json.loads(p.read_text(encoding='utf-8')) for p in ROOT.glob('*.json')]
    return sorted([{k: v for k, v in r.items() if k not in ('base', 'proposal')}
                   for r in rows if name is None or r['project'] == name],
                  key=lambda r: r['created_at'], reverse=True)

def create(name, text, expected_revision):
    if not isinstance(text, str) or not 1 <= len(text.strip()) <= 4000:
        raise ValueError('请输入 1～4000 字的修改想法')
    with locked():
        if not core.draft_path(name).is_file(): raise ValueError('请先保存通用项目')
        base = core.load(name)
        if base.get('version') != 2: raise ValueError('仅支持通用项目')
        if type(expected_revision) is not int or base['revision'] != expected_revision:
            raise RuntimeError('项目版本已变化，请重新打开后提交')
        now = datetime.now(timezone.utc).isoformat()
        return write({'id': uuid.uuid4().hex, 'project': name, 'text': text.strip(),
                      'status': 'pending', 'created_at': now, 'base_revision': base['revision'],
                      'base': base, 'summary': '', 'proposal': None})

def propose(ident, draft, summary):
    if draft.get('version') != 2: raise ValueError('提案须为通用项目')
    if not isinstance(summary, str) or not 1 <= len(summary.strip()) <= 4000:
        raise ValueError('请提供修改说明')
    candidate = copy.deepcopy(studio.validate(draft))
    with locked():
        r = read(ident)
        if r['status'] not in ('pending', 'reviewing'): raise RuntimeError('请求已处理，请刷新')
        if candidate['revision'] != r['base_revision']: raise RuntimeError('提案版本与请求不符')
        current = core.load(r['project'])
        if current['revision'] != r['base_revision']: raise RuntimeError('项目已更新，请基于新版本重新提交请求')
        candidate['active_dialog'] = None
        candidate.pop('input_value', None)
        r.update(status='proposed', proposal=candidate, summary=summary.strip())
        return write(r)

def mark(ident, status):
    if status not in ('reviewing', 'cancelled'): raise ValueError('状态无效')
    with locked():
        r = read(ident)
        if r['status'] in ('applied', 'cancelled'): raise RuntimeError('请求已结束')
        if status == 'reviewing' and r['status'] != 'pending': raise RuntimeError('请求已被处理')
        r['status'] = status
        return write(r)

def apply(ident):
    with locked():
        r = read(ident)
        if r['status'] != 'proposed': raise RuntimeError('没有可应用的提案')
        # core.save performs an independent, cross-process revision check under its lock.
        result = core.save(r['project'], r['proposal'], r['base_revision'])
        r.update(status='applied', applied_revision=result['revision'])
        write(r)
        return result
