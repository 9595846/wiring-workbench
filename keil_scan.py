"""Bounded, read-only Keil source evidence scanner. Never runs project code."""
import hashlib,os,re
from pathlib import Path
import xml.etree.ElementTree as ET
MAX_SOURCE=1000000
IGNORE={'.git','Objects','Listings','BuildLogs','node_modules','.venv','vendor'}
def read(path,limit=MAX_SOURCE):
 if path.stat().st_size>limit:raise ValueError('文件过大：'+path.name)
 b=path.read_bytes()
 if len(b)>limit:raise ValueError('文件过大：'+path.name)
 for enc in ('utf-8-sig','gb18030','cp1252'):
  try:return b.decode(enc)
  except UnicodeDecodeError:pass
 raise ValueError('无法解码：'+path.name)
def within(path,root):
 try:path.resolve().relative_to(root.resolve());return True
 except ValueError:return False
def projects(path):
 p=Path(path).expanduser().resolve()
 if p.is_file():
  if p.suffix.lower()!='.uvprojx':raise ValueError('请选择 .uvprojx 或工程目录')
  return [p]
 if not p.is_dir():raise ValueError('工程目录不存在')
 direct=sorted(p.glob('*.uvprojx'))
 if direct:return direct
 found=[];visited=0
 for base,dirs,files in os.walk(p,followlinks=False):
  dirs[:]=[d for d in dirs if d not in IGNORE and not (Path(base)/d).is_symlink()]
  if len(Path(base).relative_to(p).parts)>=4:dirs[:]=[]
  for name in files:
   visited+=1
   if visited>4000:raise ValueError('目录过大，请直接选择包含 uvprojx 的子目录')
   if name.lower().endswith('.uvprojx'):found.append(Path(base)/name)
  if len(found)>30:raise ValueError('工程过多，请选择更具体的目录')
 return sorted(found)
def tree(project):
 text=read(project,2000000)
 if '<!DOCTYPE' in text or '<!ENTITY' in text:raise ValueError('不支持包含实体声明的工程 XML')
 try:return ET.fromstring(text)
 except ET.ParseError as e:raise ValueError('工程 XML 无法解析：'+str(e)) from e
def strip_comments(s):
 # Preserve source offsets and line numbers, also ignore strings in evidence matching.
 pattern=r'/\*.*?\*/|//[^\n]*|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\''
 return re.sub(pattern,lambda m:''.join('\n' if c=='\n' else ' ' for c in m.group()),s,flags=re.S)
def parse_source(text,file):
 clean=strip_comments(text);macros={};macro_lines={};conditional_lines=set();stack=[]
 for lineno,line in enumerate(clean.splitlines(),1):
  if re.match(r'\s*#\s*(if|ifdef|ifndef)\b',line):stack.append(line.strip())
  if stack:conditional_lines.add(lineno)
  if re.match(r'\s*#\s*endif\b',line) and stack:stack.pop()
  m=re.match(r'\s*#\s*define\s+([A-Za-z_]\w*)\s+(.+)',line)
  if m:
   name,value=m.groups();macros.setdefault(name,[]).append(value.strip());macro_lines.setdefault(name,[]).append(lineno)
 def expand(expr,seen=()):
  if len(seen)>12:return expr
  return re.sub(r'\b[A-Za-z_]\w*\b',lambda m:'('+expand(macros[m[0]][0],(*seen,m[0]))+')' if m[0] in macros and len(macros[m[0]])==1 and m[0] not in seen else m[0],expr)
 def pins(expr):
  expanded=expand(expr)
  # Only explicit GPIO pin expressions joined with | and parentheses are resolved.
  rest=re.sub(r'GPIO_P[Ii][Nn]_\d+|GPIO_Pin_\d+|GPIO_PIN_\d+','',expanded)
  if re.sub(r'[|()\s]','',rest):return [],expanded
  return sorted(set(int(x) for x in re.findall(r'GPIO_(?:Pin|PIN)_(\d+)',expanded))),expanded
 assignments={};rows=[];unresolved=[]
 token=re.compile(r'(?P<assign>\b(?P<var>\w+)\.(?P<field>GPIO_Pin|GPIO_Mode|Pin|Mode)\s*=\s*(?P<value>[^;]+);)|(?P<call>\b(?P<func>GPIO_Init|HAL_GPIO_Init)\s*\(\s*(?P<port>[^,;]+),\s*&\s*(?P<arg>\w+)\s*\))|(?P<reset>[{}])',re.S)
 for match in token.finditer(clean):
  line=clean.count('\n',0,match.start())+1
  if match['reset']:assignments={};continue
  if match['assign']:
   assignments.setdefault(match['var'],{})[match['field']]=(match['value'].strip(),line);continue
  data=assignments.get(match['arg'],{});entry=data.get('GPIO_Pin') or data.get('Pin');mode=data.get('GPIO_Mode') or data.get('Mode')
  if not entry:
   unresolved.append({'file':file,'line':line,'reason':'初始化结构体针脚无法确定（可能跨作用域、指针或动态赋值）','code':text.splitlines()[line-1].strip()[:400]});continue
  expr,assign_line=entry;nums,expanded=pins(expr);port=re.sub(r'[()\s]','',expand(match['port']));port_match=re.fullmatch(r'GPIO([A-K])',port)
  if not port_match or not nums or any(n>15 for n in nums):
   unresolved.append({'file':file,'line':line,'reason':'端口或针脚表达式无法静态确定：'+expr,'code':text.splitlines()[line-1].strip()[:400]});continue
  symbols=re.findall(r'\b[A-Za-z_]\w*\b',expr)
  macro_evidence=[{'symbol':name,'line':ln,'code':text.splitlines()[ln-1].strip()[:400]} for name in symbols if name in macro_lines for ln in macro_lines[name]]
  conditional=line in conditional_lines or assign_line in conditional_lines or any(m['line'] in conditional_lines for m in macro_evidence)
  for num in nums:
   rows.append({'file':file,'line':line,'pin':'P'+port_match[1]+str(num),'mode':expand(mode[0]) if mode else '未知','expression':expr,'symbols':[s for s in symbols if num in pins(s)[0]],'assignment_line':assign_line,'code':text.splitlines()[line-1].strip()[:400],'assignment_code':text.splitlines()[assign_line-1].strip()[:400],'macros':macro_evidence,'conditional':conditional,'confidence':'静态候选，未验证运行路径'})
 # Expressions not resolved as an init call are not promoted to inferred pin mappings.
 for i,line in enumerate(clean.splitlines(),1):
  if re.search(r'\b(?:GPIO[ABCK]?|GPIO[A-K]|TIM\w*|AFIO)\s*->|GPIO_PinRemapConfig\s*\(',line):
   unresolved.append({'file':file,'line':i,'reason':'寄存器/重映射访问仅列证据，不据此推断最终针脚用途','code':text.splitlines()[i-1].strip()[:400]})
 return rows,unresolved

def scan(path,target_name=None):
 choices=projects(path)
 if not choices:raise ValueError('目录内未找到 Keil .uvprojx 工程')
 if len(choices)>1:return {'needs_project':True,'projects':[str(p) for p in choices]}
 project=choices[0];root=project.parent;xml=tree(project);targets=xml.findall('.//Targets/Target');names=[t.findtext('TargetName','') for t in targets]
 if len(targets)>1 and not target_name:return {'needs_target':True,'project':str(project),'targets':names}
 selected=next((t for t in targets if t.findtext('TargetName')==target_name),None) if target_name else (targets[0] if targets else None)
 if selected is None:raise ValueError('目标不存在，请重新选择')
 rows=[];unknown=[];fingerprints={str(project.relative_to(root)):hashlib.sha256(project.read_bytes()).hexdigest()};source_paths=set();skipped=[]
 for group in selected.findall('./Groups/Group'):
  group_excluded=group.findtext('./GroupOption/CommonProperty/IncludeInBuild')=='0'
  for f in group.findall('./Files/File'):
   name=f.findtext('FilePath','');p=(root/name.replace('\\','/')).resolve()
   if group_excluded or f.findtext('./FileOption/CommonProperty/IncludeInBuild')=='0':skipped.append({'file':name,'reason':'工程设置排除编译'});continue
   if p.suffix.lower() not in ('.c','.h','.cpp'):continue
   if not within(p,root):skipped.append({'file':name,'reason':'位于所选工程目录外，未读取'});continue
   if not p.is_file():skipped.append({'file':name,'reason':'文件不存在'});continue
   source_paths.add(p)
 if len(source_paths)>250:raise ValueError('目标源码过多，请缩小目标范围')
 # Include project-local quoted headers; system/external include paths are deliberately not traversed.
 includes=[root]
 for text in selected.findall('.//VariousControls/IncludePath'):
  for value in (text.text or '').split(';'):
   p=(root/value.replace('\\','/')).resolve()
   if within(p,root) and p.is_dir():includes.append(p)
 queue=list(source_paths);texts={};total=0
 while queue:
  p=queue.pop(0)
  if p in texts:continue
  if len(texts)>=350:raise ValueError('头文件依赖过多，停止扫描')
  try:content=read(p)
  except ValueError as e:skipped.append({'file':str(p.relative_to(root)),'reason':str(e)});continue
  total+=p.stat().st_size
  if total>16000000:raise ValueError('工程读取量超过 16MB，停止扫描')
  texts[p]=content
  for header in re.findall(r'^\s*#\s*include\s*"([^"\n]+)"',content,re.M):
   for parent in [p.parent,*includes]:
    candidate=(parent/header.replace('\\','/')).resolve()
    if within(candidate,root) and candidate.is_file() and candidate.suffix.lower()=='.h':queue.append(candidate);break
 for p,content in sorted(texts.items()):
  name=p.relative_to(root).as_posix();fingerprints[name]=hashlib.sha256(p.read_bytes()).hexdigest()
  if p.suffix.lower() in ('.c','.cpp'):
   r,u=parse_source(content,name);rows.extend(r);unknown.extend(u)
 return {'project':str(project),'root':str(root),'target':selected.findtext('TargetName'),'device':selected.findtext('.//Device','未知'),'defines':selected.findtext('.//Cads/VariousControls/Define',''),'files_read':len(texts),'evidence':rows[:2000],'unresolved':unknown[:500],'truncated':len(rows)>2000 or len(unknown)>500,'skipped':skipped,'fingerprints':fingerprints,'limitations':['仅支持标准外设库 GPIO_Init 与 HAL_GPIO_Init 的局部显式赋值。','未运行预处理器、编译器或程序；所有结果为静态候选，条件分支是否生效待确认。','仅展开同文件内单一定义的对象宏；跨头文件宏、动态代码、复用映射和寄存器写入不推断最终配置。','文件读取范围限所选工程目录；工程外源码会单列未读取。']}
