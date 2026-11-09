"""Read saved OLED designs via the explicitly configured local workbench."""
import json
import os
from pathlib import Path
import re
import subprocess
import urllib.parse
import urllib.request

CONFIG = Path(__file__).with_name('oled_link.local.json')

def config():
    if not CONFIG.is_file(): raise ValueError('尚未配置 OLED 软件。请按联动说明设置 oled_link.json。')
    c = json.loads(CONFIG.read_text(encoding='utf-8'))
    def resolve(value):
        p=Path(value)
        return (p if p.is_absolute() else CONFIG.parent/p).resolve()
    exe, root = resolve(c['executable']), resolve(c['workspace'])
    if exe.name != 'OLEDWorkbench.exe' or not exe.is_file() or not (root/'web/studio.html').is_file():
        raise ValueError('OLED 软件或工作区路径无效')
    return exe, root

def draft(root, name):
    if not isinstance(name,str) or not re.fullmatch(r'project_[A-Za-z0-9_-]{1,32}', name):
        raise ValueError('OLED 项目名称无效')
    path = root/'drafts'/(name+'.json')
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 2500000:
        raise ValueError('OLED 项目不存在或过大')
    d = json.loads(path.read_text(encoding='utf-8'))
    if d.get('version') != 2: raise ValueError('只支持通用 OLED 设计项目')
    return d

def listing():
    _, root = config()
    designs=[]
    for p in sorted((root/'drafts').glob('project_*.json')):
        try:
            d=draft(root,p.stem)
            designs.append({'name':p.stem,'revision':d['revision'],'pages':len(d['pages'])})
        except (ValueError,OSError,KeyError): pass
    return {'projects':designs,'note':'只读取已保存设计；编辑器中未保存的修改不显示。'}

def session(root):
    s=json.loads((root/'desktop_logs/integration-session.json').read_text(encoding='utf-8'))
    if Path(s['workspace']).resolve() != root: raise ValueError('OLED 会话工作区不匹配')
    url=urllib.parse.urlsplit(s['url'])
    if url.scheme!='http' or url.hostname!='127.0.0.1' or not url.port or url.username or url.password or url.path!='/studio':
        raise ValueError('OLED 会话地址无效')
    return f'http://127.0.0.1:{url.port}'

def call(base,path,token=None,body=None):
    headers={'X-OLED-Token':token} if token else {}
    if body is not None: headers['Content-Type']='application/json'
    req=urllib.request.Request(base+path,headers=headers,data=json.dumps(body).encode('utf-8') if body is not None else None)
    with urllib.request.urlopen(req,timeout=8) as response:
        raw=response.read(5000000)
        return json.loads(raw) if token else raw.decode('utf-8')

def preview(name, page=0, expected_revision=None):
    _,root=config()
    draft(root,name)  # Reject missing names before core.load can return defaults.
    try:
        base=session(root)
        html=call(base,'/studio')
        match=re.search(r'window\.OLED_TOKEN\s*=\s*["\']([^"\']+)',html)
        if not match: raise ValueError('OLED 软件接口不匹配')
        token=match.group(1)
        d=call(base,'/api/draft?name='+urllib.parse.quote(name),token)
        if not isinstance(page,int) or not 0<=page<len(d['pages']): raise ValueError('OLED 页面超出范围')
        changed=expected_revision is not None and d['revision']!=expected_revision
        d['page']=page
        rendered=call(base,'/api/render',token,{'draft':d})
        return {'name':name,'revision':d['revision'],'page':page,'page_name':d['pages'][page]['name'],
                'changed':changed,'png':rendered['png'],'issues':rendered['issues'],
                'note':'已保存设计的电脑预览，不代表实体 OLED 验收。'}
    except (OSError,KeyError) as exc:
        raise ValueError('OLED 工作台未运行或接口不可用，请先打开 OLED 编辑器，再刷新预览。') from exc

def launch(name, expected_revision=None):
    exe,root=config();d=draft(root,name)
    if expected_revision is not None and d['revision']!=expected_revision:
        raise ValueError('OLED 设计已更新，请刷新设计列表后重新选择。')
    subprocess.Popen([str(exe),'--project',name],cwd=str(exe.parent))
    return {'opened':True,'name':name,'revision':d['revision'],
            'note':'已打开新的编辑窗口，原有窗口及未保存内容保持不变。'}
