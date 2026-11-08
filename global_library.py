"""Versioned global module templates; never rewrites project snapshots."""
from contextlib import contextmanager
from pathlib import Path
import json,os,tempfile,threading,re
STORE=Path(__file__).resolve().parent/'module_library'
LOCK=threading.RLock()
class Conflict(ValueError):pass
@contextmanager
def locked():
 import msvcrt
 STORE.mkdir(parents=True,exist_ok=True)
 with LOCK,(STORE/'.lock').open('a+b') as f:
  f.seek(0,2)
  if not f.tell():f.write(b'0');f.flush()
  f.seek(0);msvcrt.locking(f.fileno(),msvcrt.LK_LOCK,1)
  try:yield
  finally:f.seek(0);msvcrt.locking(f.fileno(),msvcrt.LK_UNLCK,1)
def _load():
 p=STORE/'library.json'
 return json.loads(p.read_text(encoding='utf-8')) if p.exists() else {'format':1,'revision':0,'templates':{}}
def _write(data):
 fd,tmp=tempfile.mkstemp(dir=STORE,suffix='.tmp')
 try:
  with os.fdopen(fd,'w',encoding='utf-8') as f:json.dump(data,f,ensure_ascii=False,indent=2);f.flush();os.fsync(f.fileno())
  os.replace(tmp,STORE/'library.json')
 finally:
  if os.path.exists(tmp):os.unlink(tmp)
def template(raw):
 def text(v,limit=120):return isinstance(v,str) and len(v)<=limit
 def num(v):return type(v) in (int,float) and -10000<=v<=10000
 if not isinstance(raw,dict) or not text(raw.get('id')) or not re.fullmatch(r'[a-zA-Z0-9_-]{1,100}',raw['id']):raise ValueError('模板 ID 无效')
 if not text(raw.get('name')) or not raw['name'].strip() or not text(raw.get('kind')):raise ValueError('模板名称/类型无效')
 pins=raw.get('pins');clean=[];ids=set()
 if not isinstance(pins,list) or not 1<=len(pins)<=64:raise ValueError('模板需要 1～64 个针脚')
 for p in pins:
  if not isinstance(p,dict) or not text(p.get('id')) or not p['id'] or p['id'] in ids or not text(p.get('name')) or p.get('side') not in ('left','right','top','bottom') or not num(p.get('offset')) or not text(p.get('voltage')) or not text(p.get('role')):raise ValueError('针脚属性无效')
  pin={k:p[k] for k in ('id','name','side','offset','voltage','role')};ids.add(p['id'])
  if 'electrical' in p:
   e=p['electrical']
   if not isinstance(e,dict) or e.get('type') not in ('unknown','gnd','power_out','power_in','input','output','open_drain','passive') or type(e.get('required')) is not bool or e.get('pullup') not in ('unknown','present','absent'):raise ValueError('电气属性无效')
   pin['electrical']={k:e[k] for k in ('type','required','pullup')}
  clean.append(pin)
 out={'id':raw['id'],'name':raw['name'].strip(),'kind':raw['kind'],'pins':clean,'version':1}
 for k,minimum in [('w',120),('h',100)]:
  if k in raw:
   if not num(raw[k]) or raw[k]<minimum:raise ValueError('模板尺寸无效')
   out[k]=raw[k]
 if 'description' in raw:
  if not text(raw['description'],2000):raise ValueError('模板说明过长')
  out['description']=raw['description']
 return out
def read_library():
 with locked():
  data=_load()
  return {'revision':data['revision'],'modules':[versions[-1] for versions in data['templates'].values()],'history':{k:[{'version':x['version'],'name':x['name'],'pins':len(x['pins'])} for x in versions] for k,versions in data['templates'].items()}}
def seed(modules):
 if not isinstance(modules,list) or len(modules)>200:raise ValueError('初始模块库无效')
 cleaned=[template(m) for m in modules]
 if len({m['id'] for m in cleaned})!=len(cleaned):raise ValueError('模板 ID 重复')
 with locked():
  data=_load()
  if not data['templates']:
   data={'format':1,'revision':1,'templates':{m['id']:[m] for m in cleaned}};_write(data)
 return read_library()
def publish(raw,expected_revision,base_version):
 m=template(raw)
 if type(expected_revision) is not int or type(base_version) is not int or min(expected_revision,base_version)<0:raise ValueError('版本号无效')
 with locked():
  data=_load();versions=data['templates'].get(m['id'],[])
  if expected_revision!=data['revision'] or base_version!=(versions[-1]['version'] if versions else 0):raise Conflict('全局模块库已变化，请刷新全局库后重新核对再发布')
  if len(data['templates'])>=200 and not versions:raise ValueError('全局库最多 200 种模板')
  if len(versions)>=100:raise ValueError('单个模板最多保留 100 个版本')
  m['version']=base_version+1;data['templates'].setdefault(m['id'],[]).append(m);data['revision']+=1;_write(data)
 return read_library()
