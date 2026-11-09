"""Local OLED draft model and renderer; firmware files are read only."""
import copy, hashlib, json, os, re, tempfile, threading
from pathlib import Path
from PIL import Image

ROOT = Path(os.environ.get('OLED_WORKBENCH_ROOT', Path(__file__).resolve().parent)).resolve()
FIRMWARE = Path(os.environ.get('OLED_WORKBENCH_FIRMWARE', ROOT / 'firmware_baseline')).resolve()
DRAFTS = ROOT / 'drafts'
LOCK = threading.RLock()
PAGE_NAMES = ['按键与旋钮', '光敏检测', '姿态检测', '舵机测试']
MODEL_SOURCE_HASH = 'd8c45eaf9e46b653e1b7e58193ed3dc01bfec80108109bddc9cc4d80cd328093'

def source_changed(draft):
    if draft.get('version')==2: return False
    current = source_hash()
    return current != MODEL_SOURCE_HASH or draft.get('source_hash') != current

def source_hash():
    h = hashlib.sha256()
    for path in ['User/main.c','Hardware/display.c','Hardware/font.h','Hardware/zh12.h','Hardware/ui_text.h']:
        h.update((FIRMWARE/path).read_bytes())
    return h.hexdigest()

def glyphs(font_root=None):
    font_root=font_root or FIRMWARE/'Hardware'
    text=(font_root/'zh12.h').read_text(encoding='utf-8')
    zh={chr(int(code,16)):[int(x,16) for x in re.findall(r'0x([0-9a-fA-F]+)u',rows)]
        for code,rows in re.findall(r'\{0x([0-9A-Fa-f]+)u,\{([^}]+)\}\}',text)}
    font=(font_root/'font.h').read_text(encoding='utf-8')
    def table(name):
        block=re.search(r'static const uint8_t '+name+r'\[\d+\]\[5\] = \{(.*?)\};',font,re.S).group(1)
        return [[int(x,0) for x in row.split(',')] for row in re.findall(r'\{([^{}]+)\}',block)]
    return zh,table('g_letters'),table('g_digits')

def ui_text():
    content=(FIRMWARE/'Hardware/ui_text.h').read_text(encoding='utf-8')
    result={}
    for name,literal in re.findall(r'#define UI_(\w+) "([^"]*)"',content):
        result[name]=bytes(int(v,16) for v in re.findall(r'\\x([0-9A-Fa-f]{2})',literal)).decode('utf-8')
    return result

def defaults():
    u=ui_text()
    def e(id,text,y,kind='text'):
        return {'id':id,'text':text,'x':0,'y':y,'kind':kind}
    return {'version':1,'revision':0,'source_hash':MODEL_SOURCE_HASH,'page':0,'ideas':'',
      'simulation':{'key':0,'enc':0,'raw':2794,'avg':2783,'light_ok':True,'imu_ok':True,'ax':-15685,'ay':4223,'az':440,'id':112,'samples':7,'errors':0,'servo_on':False,'pulse':1500},
      'pages':[
       [e('title',u['TITLE'],0),e('label',u['INPUT'],16),e('value','',32,'keys'),e('next',u['NEXT'],48)],
       [e('title',u['LIGHT'],0),e('value','',16,'light'),e('hint',u['COVER'],32,'light_hint'),e('next',u['NEXT'],48)],
       [e('status',u['IMU_OK'],0,'imu_status'),e('xy','',16,'imu_xy'),e('z','',32,'imu_z'),e('count','',48,'imu_count')],
       [e('status',u['SERVO_OFF'],0,'servo_status'),e('value','',16,'servo_value'),e('keys',u['SERVO_KEYS'],32),e('knob',u['SERVO_KNOB'],48)]],
      'alternatives':{'light_bad':u['ADC_BAD'],'imu_bad':u['IMU_BAD'],'servo_on':u['SERVO_ON']}}

def element_text(e,s,alt):
    k=e['kind']; v=e['text']
    if k=='keys': return f"K{s['key']} ENC:{s['enc']}"
    if k=='light': return f"RAW:{s['raw']} AVG:{s['avg']}"
    if k=='light_hint': return v if s['light_ok'] else alt['light_bad']
    if k=='imu_status': return v if s['imu_ok'] else alt['imu_bad']
    if k=='imu_xy': return f"AX{s['ax']:6d} AY{s['ay']:6d}"
    if k=='imu_z': return f"AZ{s['az']:6d} ID:{s['id']:02X}"
    if k=='imu_count': return f"N:{s['samples']%100000} E:{s['errors']%100000}"
    if k=='servo_status': return alt['servo_on'] if s['servo_on'] else v
    if k=='servo_value': return f"PWM:{s['pulse']}us"
    return v

def render(draft,page=None,font_root=None,extra_glyphs=None):
    if draft.get('version')==2:
        import studio
        return studio.render(draft)
    page=draft['page'] if page is None else page
    zh,letters,digits=glyphs(font_root); zh.update(extra_glyphs or {}); image=Image.new('1',(128,64),0); pix=image.load(); issues=[]
    def pixel(x,y):
        if 0<=x<128 and 0<=y<64: pix[x,y]=1
    for e in draft['pages'][page]:
        text=element_text(e,draft['simulation'],draft['alternatives']); x=e['x']; y=e['y']
        width=sum(6 if ord(c)<128 else 12 for c in text)
        height=12 if any(ord(c)>=128 for c in text) else 8
        if x<0 or y<0 or x+width>128 or y+height>64: issues.append({'id':e['id'],'type':'overflow','message':f"{e['id']} 超出屏幕"})
        for c in text:
            if ord(c)>=128:
                if c in zh:
                    for j,row in enumerate(zh[c]):
                        for i in range(12):
                            if row & (0x8000>>i): pixel(x+i,y+j)
                else:
                    issues.append({'id':e['id'],'type':'missing','message':f'字库缺少：{c}'})
                    for i in range(11): pixel(x+i,y);pixel(x+i,y+10)
                    for j in range(11): pixel(x,y+j);pixel(x+10,y+j)
                x+=12; continue
            ch=c.upper() if 'a'<=c<='z' else c
            if 'A'<=ch<='Z': cols=letters[ord(ch)-65]
            elif '0'<=ch<='9': cols=digits[ord(ch)-48]
            elif ch==':': cols=[0,0,0x24,0,0]
            elif ch=='/': cols=[1<<(6-i) for i in range(5)]
            elif ch=='-': cols=[8]*5
            elif ch=='=': cols=[0x14]*5
            elif ch=='.': cols=[0,0,0x40,0,0]
            else:
                cols=[0]*5
                if ch!=' ': issues.append({'id':e['id'],'type':'missing','message':f'字库缺少：{c}'})
            for i,col in enumerate(cols):
                for j in range(7):
                    if col & (1<<j): pixel(x+i,y+j)
            x+=6
    return image,issues

def validate(d):
    if isinstance(d,dict) and d.get('version')==2:
        import studio
        return studio.validate(d)
    if not isinstance(d,dict) or d.get('version')!=1 or not isinstance(d.get('revision'),int): raise ValueError('草稿版本或修订号无效')
    if not isinstance(d.get('page'),int) or not 0<=d['page']<4: raise ValueError('页面无效')
    if not isinstance(d.get('ideas'),str) or len(d['ideas'])>10000: raise ValueError('便签过长')
    if not isinstance(d.get('source_hash'),str): raise ValueError('缺少工程来源摘要')
    base=defaults()
    if not isinstance(d.get('pages'),list) or len(d['pages'])!=4: raise ValueError('页面结构无效')
    for page, original in zip(d['pages'],base['pages']):
        if not isinstance(page,list) or len(page)!=len(original): raise ValueError('页面元素无效')
        for e,ref in zip(page,original):
            if e.get('id')!=ref['id'] or e.get('kind')!=ref['kind']: raise ValueError('元素标识无效')
            if not isinstance(e.get('text'),str) or len(e['text'])>100: raise ValueError('文字过长')
            if any(type(e.get(k)) is not int or not -256<=e[k]<=256 for k in ('x','y')): raise ValueError('坐标无效')
    s=d.get('simulation',{})
    for key,old in base['simulation'].items():
        if type(s.get(key)) is not type(old): raise ValueError('模拟参数无效: '+key)
        if type(old) is int and not -32768<=s[key]<=999999: raise ValueError('模拟参数超范围: '+key)
    if not isinstance(d.get('alternatives'),dict) or any(not isinstance(d['alternatives'].get(k),str) or len(d['alternatives'][k])>100 for k in base['alternatives']): raise ValueError('备用文字无效')
    return d

def draft_path(name):
    if not re.fullmatch(r'[A-Za-z0-9_\u4e00-\u9fff-]{1,40}',name): raise ValueError('草稿名限 40 字以内的汉字、英文字母、数字、下划线和短横线')
    return DRAFTS/(name+'.json')

def load(name):
    p=draft_path(name)
    return validate(json.loads(p.read_text(encoding='utf-8'))) if p.exists() else defaults()

def save(name,draft,expected):
    draft_path(name)
    if type(expected) is not int or expected < 0: raise ValueError('预期修订号无效')
    DRAFTS.mkdir(parents=True,exist_ok=True)
    # A cross-process lock makes the revision check and replace one transaction.
    import msvcrt
    lockpath=DRAFTS/'.lock'
    with LOCK, lockpath.open('a+b') as lock:
        lock.seek(0,2)
        if lock.tell()==0: lock.write(b'0');lock.flush()
        lock.seek(0)
        msvcrt.locking(lock.fileno(),msvcrt.LK_LOCK,1)
        try:
            current=load(name)
            if current['revision']!=expected: raise RuntimeError(f"草稿已被其他窗口修改（当前版本 {current['revision']}），请重新读取。")
            d=copy.deepcopy(validate(draft));d['revision']=expected+1
            fd,tmp=tempfile.mkstemp(dir=DRAFTS,suffix='.tmp')
            try:
                with os.fdopen(fd,'w',encoding='utf-8') as f: json.dump(d,f,ensure_ascii=False,indent=2)
                os.replace(tmp,draft_path(name))
            finally:
                if os.path.exists(tmp): os.unlink(tmp)
            return d
        finally:
            lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_UNLCK,1)
