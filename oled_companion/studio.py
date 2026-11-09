"""Portable 128x64 scene projects. Actions are data, never executable code."""
import copy, io, base64, re
from PIL import Image, ImageDraw
import core

def new():
    return {'version':2,'revision':0,'source_hash':'portable-font-v1','font_mode':'chinese_preview','title':'新界面项目','page':0,'ideas':'','variables':{'value':0},'active_dialog':None,'pages':[{'name':'主页面','elements':[element('text')],'bindings':{}}]}

def element(kind):
    e={'id':'element','kind':kind,'x':0,'y':0,'text':'主页面','w':128,'h':64}
    if kind=='dialog':e.update(x=8,y=8,w=112,h=48,text='确认操作',mode='confirm',variable='value',minimum=0,maximum=100,step=1,confirm={'type':'close'},cancel={'type':'close'})
    if kind=='image':e.update(text='',bits='0'*8192)
    return e

def validate(d):
    def require(ok,msg):
        if not ok:raise ValueError(msg)
    require(type(d.get('revision')) is int and d['revision']>=0,'修订号无效')
    require(isinstance(d.get('title'),str) and len(d['title'])<=80,'项目标题无效')
    require(isinstance(d.get('ideas'),str) and len(d['ideas'])<=10000,'便签无效')
    require(d.get('font_mode','firmware') in ('firmware','chinese_preview'),'字库模式无效')
    pages=d.get('pages');require(isinstance(pages,list) and 1<=len(pages)<=32,'需要 1～32 页')
    require(type(d.get('page')) is int and 0<=d['page']<len(pages),'当前页面无效')
    variables=d.get('variables');require(isinstance(variables,dict) and len(variables)<=32,'变量无效')
    if 'input_value' in d:require(type(d['input_value']) is int and -999999<=d['input_value']<=999999,'输入值无效')
    for k,v in variables.items():require(re.fullmatch(r'[A-Za-z_\u4e00-\u9fff][A-Za-z0-9_\u4e00-\u9fff]{0,23}',k) and type(v) is int and -999999<=v<=999999,'变量名或数值无效')
    for p in pages:
        require(isinstance(p.get('name'),str) and len(p['name'])<=80,'页面名称无效')
        require(isinstance(p.get('elements'),list) and len(p['elements'])<=32,'每页最多 32 元素')
        ids=set()
        for e in p['elements']:
            require(isinstance(e.get('id'),str) and e['id'] not in ids,'元素 ID 重复');ids.add(e['id'])
            require(e.get('kind') in ('text','image','dialog'),'不支持的元素')
            require(isinstance(e.get('text'),str) and len(e['text'])<=200,'文字无效')
            for k in ('x','y','w','h'):require(type(e.get(k)) is int and -256<=e[k]<=256,'坐标或大小无效')
            if e['kind']=='image':require(1<=e['w']<=128 and 1<=e['h']<=64 and isinstance(e.get('bits'),str) and len(e['bits'])==e['w']*e['h'] and set(e['bits'])<=set('01'),'图片像素无效')
            if e['kind']=='dialog':
                require(24<=e['w']<=128 and 24<=e['h']<=64,'弹窗尺寸至少 24×24')
                require(e.get('mode') in ('message','confirm','number'),'弹窗类型无效')
                require(e.get('variable') in variables,'弹窗变量不存在')
                require(all(type(e.get(k)) is int for k in ('minimum','maximum','step')) and -999999<=e['minimum']<=e['maximum']<=999999 and 1<=e['step']<=999999,'数值输入范围无效')
        def action(a):
            require(isinstance(a,dict) and a.get('type') in ('none','close','open','goto','set','add'),'动作无效')
            if a['type']=='goto':require(type(a.get('page')) is int and 0<=a['page']<len(pages),'跳页目标不存在')
            if a['type']=='open':require(any(e['id']==a.get('target') and e['kind']=='dialog' for e in p['elements']),'弹窗目标不存在')
            if a['type'] in ('set','add'):require(a.get('variable') in variables and type(a.get('value')) is int and -999999<=a['value']<=999999,'变量动作无效')
        require(isinstance(p.get('bindings'),dict) and set(p['bindings'])<=set(['KEY1','KEY2','KEY3','KEY4','LEFT','RIGHT']),'按键绑定无效')
        for a in p['bindings'].values():action(a)
        for e in p['elements']:
            if e['kind']=='dialog':action(e['confirm']);action(e['cancel'])
    active=d.get('active_dialog')
    require(active is None or any(e['id']==active and e['kind']=='dialog' for e in pages[d['page']]['elements']),'当前弹窗无效')
    return d

def run(d,event):
    d=copy.deepcopy(validate(d));p=d['pages'][d['page']]
    active=next((e for e in p['elements'] if e['id']==d['active_dialog']),None)
    a=p['bindings'].get(event,{'type':'none'})
    if active:
        if event in ('LEFT','RIGHT') and active['mode']=='number':
            k=active['variable'];value=d.get('input_value',d['variables'][k]);d['input_value']=max(active['minimum'],min(active['maximum'],value+active['step']*(1 if event=='RIGHT' else -1)));return d
        if event not in ('KEY1','KEY2'):return d
        if event=='KEY1' and active['mode']=='number':d['variables'][active['variable']]=max(active['minimum'],min(active['maximum'],d.get('input_value',d['variables'][active['variable']])))
        a=active['confirm' if event=='KEY1' else 'cancel'];d['active_dialog']=None;d.pop('input_value',None)
    t=a['type']
    if t=='goto':d['page']=a['page'];d['active_dialog']=None
    elif t=='open':
        d['active_dialog']=a['target'];e=next(e for e in p['elements'] if e['id']==a['target']);d['input_value']=max(e['minimum'],min(e['maximum'],d['variables'][e['variable']]))
    elif t=='close':d['active_dialog']=None
    elif t in ('set','add'):k=a['variable'];d['variables'][k]=max(-999999,min(999999,a['value']+(d['variables'][k] if t=='add' else 0)))
    return d

def render(d):
    validate(d);image=Image.new('1',(128,64));issues=[];draw=ImageDraw.Draw(image)
    def text(e,s,x,y):
        for name in re.findall(r'\{([A-Za-z_\u4e00-\u9fff][A-Za-z0-9_\u4e00-\u9fff]*)\}',s):
            if name not in d['variables']:issues.append({'id':e['id'],'type':'variable','message':'变量不存在：'+name})
        s=re.sub(r'\{([A-Za-z_\u4e00-\u9fff][A-Za-z0-9_\u4e00-\u9fff]*)\}',lambda m:str(d['variables'].get(m[1],m[0])),s)
        fake={'page':0,'pages':[[{'id':e['id'],'kind':'text','text':s,'x':x,'y':y}]],'simulation':{},'alternatives':{}}
        extra={}
        if d.get('font_mode')=='chinese_preview':
            import chinese_font
            known=core.glyphs(core.ROOT/'fonts')[0]
            for c in set(s):
                if ord(c)>=128 and c not in known:
                    try: bitmap=chinese_font.rows(c)
                    except OSError: bitmap=None
                    if bitmap is not None:extra[c]=bitmap
            if extra:issues.append({'id':e['id'],'type':'preview_font','message':'中文设计字模仅用于电脑预览；应用到固件时需补充字库'})
        layer,warnings=core.render(fake,font_root=core.ROOT/'fonts',extra_glyphs=extra);image.paste(1,(0,0,128,64),layer);issues.extend(warnings)
    for e in d['pages'][d['page']]['elements']:
        if e['kind']=='text':text(e,e['text'],e['x'],e['y'])
        elif e['kind']=='image':
            tile=Image.new('1',(e['w'],e['h']));tile.putdata([int(v) for v in e['bits']]);image.paste(tile,(e['x'],e['y']))
        if e['kind']!='text' and (e['x']<0 or e['y']<0 or e['x']+e['w']>128 or e['y']+e['h']>64):issues.append({'id':e['id'],'type':'overflow','message':e['id']+' 超出屏幕'})
    for e in d['pages'][d['page']]['elements']:
        if e['kind']=='dialog' and e['id']==d['active_dialog']:
            x,y,w,h=e['x'],e['y'],e['w'],e['h'];draw.rectangle((x,y,x+w-1,y+h-1),fill=0,outline=1);text(e,e['text'],x+4,y+4)
            if sum(6 if ord(c)<128 else 12 for c in e['text'])>w-8:issues.append({'id':e['id'],'type':'overflow','message':e['id']+' 标题超出弹窗宽度'})
            if e['mode']=='number':text(e,str(d.get('input_value',d['variables'][e['variable']])),x+4,y+18)
            text(e,'1确认 2取消',x+4,y+h-13)
    return image,issues

def convert_image(data):
    raw=base64.b64decode(data['data'],validate=True)
    if len(raw)>1500000:raise ValueError('图片最大 1.5 MB')
    with Image.open(io.BytesIO(raw)) as src:
        if src.width*src.height>16000000:raise ValueError('图片像素过大')
        from PIL import ImageOps
        rgba=src.convert('RGBA');bg=Image.new('RGBA',rgba.size,'white');bg.alpha_composite(rgba);gray=bg.convert('L')
        size=(int(data.get('w',128)),int(data.get('h',64)))
        if not 1<=size[0]<=128 or not 1<=size[1]<=64:raise ValueError('图片尺寸超范围')
        gray=ImageOps.fit(gray,size) if data.get('fit')=='crop' else ImageOps.pad(gray,size,color=255)
        threshold=int(data.get('threshold',128))
        if not 0<=threshold<=255:raise ValueError('阈值超范围')
        bits=''.join('1' if (v<threshold)^bool(data.get('invert')) else '0' for v in gray.tobytes())
        return dict(element('image'),w=size[0],h=size[1],bits=bits)
