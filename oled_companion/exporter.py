"""Generate reviewable C source files for the verified display_pixel adapter.
Never edits firmware or project files. Does not invoke compilers or hardware.
"""
import copy,hashlib,json,re,os,tempfile,threading
from pathlib import Path
import core,studio,chinese_font
ROOT=core.ROOT
EXPORTS=ROOT/'exports'
LOCK=threading.RLock()
EVENTS=['KEY1','KEY2','KEY3','KEY4','LEFT','RIGHT']
PATTERN=re.compile(r'\{([A-Za-z_\u4e00-\u9fff][A-Za-z0-9_\u4e00-\u9fff]*)\}')

def profile():
    p=json.loads((ROOT/'export_profile.json').read_text(encoding='utf-8'))
    for name,digest in p['sha256'].items():
        if hashlib.sha256((core.FIRMWARE/name).read_bytes()).hexdigest()!=digest:
            raise ValueError('工程适配基线已变化，需重新核对后导出：'+name)
    return p

def generate(draft):
    if draft.get('version')!=2:raise ValueError('请先在通用工作台中创建或打开 v2 项目')
    d=copy.deepcopy(studio.validate(draft));p=profile();d['active_dialog']=None;d.pop('input_value',None)
    if len(json.dumps(d,ensure_ascii=False).encode())>2000000:raise ValueError('项目过大，请拆分页面')
    variables=list(d['variables']);texts=[];glyphs=[];glyph_map={};image_data=[];elements=[];pages=[];dialogs=[];dialog_map={};warnings=[]
    known=core.glyphs(ROOT/'fonts')[0]
    def glyph(c):
        if c in glyph_map:return glyph_map[c]
        extra={}
        if ord(c)>=128 and c not in known and d.get('font_mode')=='chinese_preview':
            rows=chinese_font.rows(c)
            if rows is not None:extra[c]=rows
        fake={'page':0,'pages':[[{'id':'glyph','kind':'text','text':c,'x':0,'y':0}]],'simulation':{},'alternatives':{}}
        im,issues=core.render(fake,font_root=ROOT/'fonts',extra_glyphs=extra)
        if issues:raise ValueError('无法导出字模：'+repr(c)+'。请使用中文设计预览或替换不支持的字符。')
        width=6 if ord(c)<128 else 12;height=8 if ord(c)<128 else 12
        rows=[sum(0x8000>>x for x in range(width) if im.getpixel((x,y))) for y in range(12)]
        glyph_map[c]=len(glyphs);glyphs.append((width,height,rows));return glyph_map[c]
    def text(s):
        tokens=[];pos=0
        for match in PATTERN.finditer(s):
            tokens.extend(glyph(c) for c in s[pos:match.start()])
            if match[1] not in variables:raise ValueError('文本引用不存在的变量：'+match[1])
            tokens.append(-1-variables.index(match[1]));pos=match.end()
        tokens.extend(glyph(c) for c in s[pos:]);texts.append(tokens);return len(texts)-1
    digits=[glyph(c) for c in '0123456789'];minus=glyph('-')
    for page_index,pg in enumerate(d['pages']):
        for e in pg['elements']:
            if e['kind']=='dialog':dialog_map[(page_index,e['id'])]=len(dialogs);dialogs.append((page_index,e))
    footer=text('1确认 2取消') if dialogs else text('')
    def action(a,pi):
        t=a['type'];kind=['none','close','open','goto','set','add'].index(t);target=0;value=0
        if t=='open':target=dialog_map[(pi,a['target'])]
        if t=='goto':target=a['page']
        if t in ('set','add'):target=variables.index(a['variable']);value=a['value']
        return '{%d,%d,%d}'%(kind,target,value)
    bindings=[]
    for pi,pg in enumerate(d['pages']):
        start=len(elements)
        for e in pg['elements']:
            if e['kind']=='dialog':continue
            if e['kind']=='text':ref=text(e['text']);kind=0
            else:
                bits=e['bits'];packed=[int(bits[i:i+8].ljust(8,'0'),2) for i in range(0,len(bits),8)];ref=len(image_data);image_data.append(packed);kind=1
            elements.append('{%d,%d,%d,%d,%d,%d}'%(kind,e['x'],e['y'],e['w'],e['h'],ref))
        pages.append('{%d,%d}'%(start,len(elements)-start))
        bindings.append('{'+','.join(action(pg['bindings'].get(k,{'type':'none'}),pi) for k in EVENTS)+'}')
        check=copy.deepcopy(d);check['page']=pi;_,issues=studio.render(check)
        for e in pg['elements']:
            if e['kind']=='dialog':check['active_dialog']=e['id'];_,extra=studio.render(check);issues.extend(extra)
        warnings.extend(f"第{pi+1}页：{i['message']}" for i in issues if i['type']!='preview_font')
    dialog_rows=[]
    for pi,e in dialogs:
        dialog_rows.append('{%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%s,%s}'%(e['x'],e['y'],e['w'],e['h'],text(e['text']),variables.index(e['variable']),int(e['mode']=='number'),e['minimum'],e['maximum'],e['step'],action(e['confirm'],pi),action(e['cancel'],pi)))
    h='''#ifndef OLED_UI_ASSETS_H
#define OLED_UI_ASSETS_H
#include <stdint.h>
typedef struct {uint8_t width,height;uint16_t rows[12];} UiGlyph;
typedef struct {uint16_t length;const int16_t *tokens;} UiText;
typedef struct {int16_t kind,x,y,w,h,ref;} UiElement;
typedef struct {uint16_t first,count;} UiPage;
typedef struct {int16_t kind,target;int32_t value;} UiAction;
typedef struct {int16_t x,y,w,h,title,variable,number;int32_t minimum,maximum,step;UiAction confirm,cancel;} UiDialog;
extern const UiGlyph ui_glyphs[];
extern const UiText ui_texts[];
extern const UiElement ui_elements[];
extern const UiPage ui_pages[];
extern const UiDialog ui_dialogs[];
extern const UiAction ui_bindings[][6];
extern const uint8_t *const ui_images[];
extern const int32_t ui_initial[];
extern const uint16_t ui_digits[10];
'''
    h+=f'#define UI_VAR_COUNT {len(variables)}u\n#define UI_VAR_STORAGE {max(1,len(variables))}u\n#define UI_PAGE_COUNT {len(pages)}u\n#define UI_START_PAGE {d["page"]}u\n#define UI_MINUS {minus}u\n#define UI_DIALOG_FOOTER {footer}u\n'
    h+='\n'.join(f'#define UI_VAR_{i} {i}u' for i in range(len(variables)))+'\n'
    h+='\n'.join(f'#define UI_VAR_NAME_{name} {i}u' for i,name in enumerate(variables) if re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*',name))+'\n#endif\n'
    c=['#include "ui_assets.h"']
    def array(type,name,rows,empty):c.append(f'const {type} {name}[] = {{'+',\n'.join(rows or [empty])+'};')
    array('UiGlyph','ui_glyphs',['{%d,%d,{%s}}'%(w,hh,','.join(str(r) for r in rr)) for w,hh,rr in glyphs],'{0}')
    for i,t in enumerate(texts):c.append('static const int16_t text_%d[] = {%s};'%(i,','.join(map(str,t or [0]))))
    array('UiText','ui_texts',['{%d,text_%d}'%(len(t),i) for i,t in enumerate(texts)],'{0,0}')
    for i,b in enumerate(image_data):c.append('static const uint8_t image_%d[] = {%s};'%(i,','.join(map(str,b))))
    c.append('const uint8_t *const ui_images[] = {'+','.join('image_'+str(i) for i in range(len(image_data)))+'0};' if not image_data else 'const uint8_t *const ui_images[] = {'+','.join('image_'+str(i) for i in range(len(image_data)))+'};')
    array('UiElement','ui_elements',elements,'{0}')
    array('UiPage','ui_pages',pages,'{0}')
    array('UiDialog','ui_dialogs',dialog_rows,'{0}')
    c.append('const UiAction ui_bindings[][6] = {'+',\n'.join(bindings)+'};')
    array('int32_t','ui_initial',[str(v) for v in d['variables'].values()],'0')
    c.append('const uint16_t ui_digits[10] = {'+','.join(map(str,digits))+'};')
    estimated=sum(len(b) for b in image_data)+len(glyphs)*26+sum(len(t)*2+8 for t in texts)+max(1,len(elements))*12+len(pages)*52+max(1,len(dialogs))*44
    if estimated>48000:raise ValueError(f'界面静态数据估算 {estimated} 字节，超过本适配的 48000 字节预算；请减少图片/页面。最终容量以链接结果为准。')
    files={'ui_design.json':json.dumps(d,ensure_ascii=False,indent=2),'ui_assets.h':h,'ui_assets.c':'\n'.join(c)+'\n'}
    for name in ['ui_pages.h','ui_pages.c','ui_actions.h','ui_actions.c']:files[name]=(ROOT/'export_runtime'/name).read_text(encoding='ascii')
    manifest={'format':1,'adapter':p['id'],'design_sha256':hashlib.sha256(files['ui_design.json'].encode()).hexdigest(),'profile':p,'variables':{f'UI_VAR_{i}':k for i,k in enumerate(variables)},'pages':[pg['name'] for pg in d['pages']],'glyphs':len(glyphs),'images':len(image_data),'estimated_const_bytes':estimated,'warnings':list(dict.fromkeys(warnings))+['动态变量变长可能超出屏幕，需测试极值','资源字节数为估算，完整程序 Flash/RAM 占用需 Keil 链接确认'],'validation':{'host_compile':'not_run_for_this_export','keil_compile':'not_run','hardware':'not_run'}}
    files['接入说明.md']=guide(manifest)
    manifest['files']={name:hashlib.sha256(content.encode()).hexdigest() for name,content in files.items()}
    files['manifest.json']=json.dumps(manifest,ensure_ascii=False,indent=2)
    return files,manifest

def guide(m):
    return '''# 界面资源接入说明

这是待审阅的界面源文件，不是完整 Keil 工程，也不是可烧录 HEX。导出没有修改 defuse_box/firmware。适配已核对的 STM32F103C8、标准外设库工程，调用现有 display_clear/display_pixel；保留 display_task 的非阻塞刷新。

## 文件与接入顺序

1. 先确认 ui_design.json 是要应用的设计。manifest.json 记录设计、适配文件指纹和资源估算。
2. 经确认后将 ui_assets.c/.h、ui_pages.c/.h、ui_actions.c/.h 放入当前工程选定的目录，例如 Hardware/UI。将三个 .c 加入现有 Project.uvprojx，并将目录加入原有 Include Paths。不要替换整份工程文件。
3. main.c 加入 ui_pages.h、ui_assets.h，在 display_init 后调用 ui_init()。ui_init 使用草稿导出时选中的页面作为启动页。
4. 将原 draw(now) 的调用替换为 ui_draw()。主循环仍调用 display_task(now)。不要在同一周期同时画旧页面和新界面。
5. 将 buttons_task 返回的去抖按键事件交给 ui_event(UI_KEY1...UI_KEY4)，并将 encoder_delta 的每格变化交给 UI_LEFT/UI_RIGHT。这不是 GPIO 引脚号。
6. 审查原 handle_keys、rotate 和串口 PAGE/SERVO 命令：它们已有翻页、舵机功能，不能把同一按键同时交给新旧处理器。先明确哪些旧功能保留，页面切换/退出须协调原 stop_servo；保留 servo_task 的 15 秒闲置保护及 outputs_task。
7. 保留 IMU、光敏和串口后台采样。通过 ui_set_variable(UI_VAR_n, value) 更新界面变量；ui_get_variable 读取确认后的设置值。导出动作只修改界面变量，不直接驱动舵机、LED 或蜂鸣器。

事件接入示意（应替代冲突的旧处理位置，不可原样叠加）：

```c
unsigned i;
/* keys is the debounced mask from buttons_task(now). */
for (i = 0; i < 4; ++i) {
    if (keys & (1u << i)) ui_event(UI_KEY1 + i);
}
/* Consume a bounded number of encoder detents each loop;
   keep remaining detents for the next loop to avoid long blocking work. */
```

## 字库与像素

导出字模来自当前设计模式。中文设计模式需要的新增汉字已转为随文件保存的单色点阵；不依赖 STM32 上的系统字体，也不修改旧 zh12.h。文件只包含整数数据和 ASCII C 标识符，中文变量通过编号映射。不能导出的字符会阻止导出。图片按行、每字节高位先行、尾部补零打包；由 ui_pages.c 逐像素绘制，不要求修改原驱动的图片格式。

文字动态变量以十进制显示，取值限 -999999～999999。数值弹窗先修改临时值，确认提交，取消丢弃；一项事件执行一项动作。屏幕外像素由原 display_pixel 裁切。页面名和便签只保存在设计文件，不变成可执行代码。

## 验收

请先在 Keil 编译并检查完整工程 Flash/RAM，然后烧录实体板，验证所有页面、变量极值、弹窗确认/取消、连续旋钮和图片。导出完成不是编译通过，主机编译不是 Keil 完整工程链接，预览不是实物验收。

本次变量映射：

'''+ '\n'.join(f'- `{key}` → `{value}`' for key,value in m['variables'].items())+f'\n\n静态资源估算：{m["estimated_const_bytes"]} 字节（不含完整固件与运行时全部开销）。\n'

def export(draft,name):
    core.draft_path(name) # Reuse the constrained filename policy, never an arbitrary path.
    files,manifest=generate(draft)
    EXPORTS.mkdir(exist_ok=True)
    out=EXPORTS/name
    import msvcrt
    with LOCK,(EXPORTS/'.lock').open('a+b') as lock:
        lock.seek(0,2)
        if lock.tell()==0:lock.write(b'0');lock.flush()
        lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_LOCK,1)
        try:
            if out.exists():
                previous=out/'manifest.json'
                if not previous.exists():raise ValueError('导出目录已有非生成内容，请使用其他名称')
                old=json.loads(previous.read_text(encoding='utf-8'))
                for fn in files:
                    path=out/fn
                    if fn=='manifest.json':continue
                    if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest()!=old.get('files',{}).get(fn):raise ValueError('已导出文件被手工修改，拒绝覆盖：'+fn)
            out.mkdir(exist_ok=True)
            for fn,content in files.items():
                fd,tmp=tempfile.mkstemp(dir=out,suffix='.tmp')
                try:
                    with os.fdopen(fd,'w',encoding='utf-8',newline='\n') as stream:stream.write(content)
                    os.replace(tmp,out/fn)
                finally:
                    if os.path.exists(tmp):os.unlink(tmp)
        finally:lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_UNLCK,1)
    return {'directory':str(out.resolve()),'name':name,'files':list(files),'manifest':manifest}

def read_file(name,filename):
    core.draft_path(name)
    allowed={'ui_design.json','ui_assets.c','ui_assets.h','ui_pages.c','ui_pages.h','ui_actions.c','ui_actions.h','manifest.json','接入说明.md'}
    if filename not in allowed:raise ValueError('不允许读取此导出文件')
    return (EXPORTS/name/filename).read_bytes()
