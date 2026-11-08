"""Single project store shared by HTTP and MCP, with revision leases and restore points."""
from pathlib import Path
from contextlib import contextmanager
import json,os,re,tempfile,threading,hashlib,uuid,subprocess,shutil
from datetime import datetime,timezone
DATA=Path(__file__).resolve().parent/'projects'
LOCK=threading.RLock()
class Conflict(ValueError):pass
def engine(action,**data):
 node=shutil.which('node')
 if not node:raise ValueError('需要安装 Node.js 并加入 PATH')
 payload=json.dumps({'action':action,**data},ensure_ascii=False)
 if len(payload.encode('utf-8'))>4000000:raise ValueError('项目请求超过 4MB')
 try:r=subprocess.run([node,str(Path(__file__).with_name('bridge.mjs'))],input=payload,text=True,encoding='utf-8',capture_output=True,timeout=45)
 except subprocess.TimeoutExpired:raise ValueError('模型处理超时，未保存修改')
 try:reply=json.loads(r.stdout)
 except ValueError:raise ValueError('模型处理失败：'+r.stderr[-300:])
 if not reply.get('ok'):raise ValueError(reply.get('error','模型校验失败'))
 return reply['result']
def path_for(name,data=None):
 root=Path(data or DATA);root.mkdir(parents=True,exist_ok=True)
 if not isinstance(name,str) or not re.fullmatch('[A-Za-z0-9_-]{1,70}',name):raise ValueError('无效项目编号')
 p=root/(name+'.json')
 if p.resolve().parent!=root.resolve():raise ValueError('无效项目路径')
 return p
@contextmanager
def locked(root):
 import msvcrt
 root=Path(root);root.mkdir(parents=True,exist_ok=True)
 with LOCK,(root/'.store.lock').open('a+b') as f:
  f.seek(0,2)
  if not f.tell():f.write(b'0');f.flush()
  f.seek(0);msvcrt.locking(f.fileno(),msvcrt.LK_LOCK,1)
  try:yield
  finally:f.seek(0);msvcrt.locking(f.fileno(),msvcrt.LK_UNLCK,1)
def _read(p):
 if p.stat().st_size>24000000:raise ValueError('项目文件过大')
 return json.loads(p.read_text(encoding='utf-8'))
def read(name,data=None):return _read(path_for(name,data))
def listing(data=None):
 root=Path(data or DATA);root.mkdir(parents=True,exist_ok=True);out=[]
 for p in root.glob('*.json'):
  try:
   x=read(p.stem,root);out.append({'id':p.stem,'title':x['package']['doc']['title'],'revision':x['revision']})
  except (ValueError,OSError,KeyError):pass
 return out
def atomic(p,obj):
 fd,tmp=tempfile.mkstemp(dir=p.parent,suffix='.tmp')
 try:
  with os.fdopen(fd,'w',encoding='utf-8') as f:json.dump(obj,f,ensure_ascii=False,indent=2);f.flush();os.fsync(f.fileno())
  os.replace(tmp,p)
 finally:
  if os.path.exists(tmp):os.unlink(tmp)
def digest(pkg):return hashlib.sha256(json.dumps(pkg,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
def history_dir(name,data=None):
 root=path_for(name,data).parent;folder=root/'.history'/name
 if not folder.resolve().is_relative_to(root.resolve()):raise ValueError('恢复点目录越界')
 folder.mkdir(parents=True,exist_ok=True)
 return folder
def _checkpoint(name,current,label,actor,data=None):
 ident=uuid.uuid4().hex;record={'id':ident,'revision':current['revision'],'created_at':datetime.now(timezone.utc).isoformat(),'label':str(label)[:120],'actor':actor,'package':current['package'],'sha256':digest(current['package'])};atomic(history_dir(name,data)/(ident+'.json'),record);return {k:v for k,v in record.items() if k not in ('package','sha256')}
def expected(current,revision):
 if type(revision) is not int or revision<0:raise ValueError('版本号无效')
 if current['revision']!=revision:raise Conflict('项目已被网页或 MCP 修改，请重新读取，或另存副本')
def write(name,pkg,revision,actor='web',label='修改前自动恢复点',data=None,force_revision=False):
 pkg=engine('validate',package=pkg);p=path_for(name,data)
 with locked(p.parent):
  old=_read(p) if p.exists() else {'revision':0};expected(old,revision)
  if old.get('package')==pkg and not force_revision:return dict(old,unchanged=True)
  checkpoint=_checkpoint(name,old,label,actor,data) if 'package'in old else None
  result={'revision':revision+1,'package':pkg};atomic(p,result)
  return dict(result,checkpoint=checkpoint)
def edit(name,operations,revision):
 current=read(name);expected(current,revision);result=engine('edit',package=current['package'],operations=operations)
 saved=write(name,result['package'],revision,'mcp','MCP 编辑前自动恢复点');saved['operations']=result['results'];return saved
def checkpoints(name,data=None):
 read(name,data);out=[]
 for p in history_dir(name,data).glob('*.json'):
  r=_read(p);out.append({k:r[k] for k in ('id','revision','created_at','label','actor')})
 return sorted(out,key=lambda r:r['created_at'],reverse=True)
def create_checkpoint(name,revision,label='手动恢复点',data=None):
 p=path_for(name,data)
 with locked(p.parent):
  current=_read(p);expected(current,revision);return _checkpoint(name,current,label,'manual',data)
def restore(name,ident,revision,actor='mcp',data=None):
 if not isinstance(ident,str) or not re.fullmatch('[0-9a-f]{32}',ident):raise ValueError('恢复点编号无效')
 folder=history_dir(name,data);p=folder/(ident+'.json')
 if p.resolve().parent!=folder.resolve():raise ValueError('恢复点路径越界')
 r=_read(p)
 if digest(r['package'])!=r['sha256']:raise ValueError('恢复点内容校验失败')
 return write(name,r['package'],revision,actor,'恢复旧内容前自动恢复点',data,force_revision=True)
