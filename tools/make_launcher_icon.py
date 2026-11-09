"""Create the original circuit-and-screen app mark as PNG/ICO and editable SVG."""
from pathlib import Path
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1]/'assets/launcher'
ROOT.mkdir(parents=True,exist_ok=True)
svg='''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">
<rect x="8" y="8" width="496" height="496" rx="112" fill="#23483d"/>
<rect x="172" y="112" width="254" height="240" rx="28" fill="#f7efdd"/>
<rect x="196" y="138" width="206" height="164" rx="12" fill="#102b24"/>
<path d="M220 252h34v-40h40v24h38v-54h42" fill="none" stroke="#a9d7b0" stroke-width="16" stroke-linejoin="round"/>
<path d="M96 170h36v94h38M96 366h180v-14" fill="none" stroke="#d6ad6d" stroke-width="20" stroke-linecap="round" stroke-linejoin="round"/>
<circle cx="96" cy="170" r="20" fill="#f7efdd"/><circle cx="96" cy="366" r="20" fill="#f7efdd"/>
<circle cx="300" cy="329" r="8" fill="#23483d"/></svg>'''
(ROOT/'workbench.svg').write_text(svg,encoding='utf-8')
scale=2
im=Image.new('RGBA',(1024,1024));d=ImageDraw.Draw(im)
def box(x):return tuple(int(v*scale) for v in x)
def line(points,fill,width):d.line([(int(x*scale),int(y*scale)) for x,y in points],fill=fill,width=width*scale,joint='curve')
d.rounded_rectangle(box((8,8,504,504)),radius=112*scale,fill='#23483d')
d.rounded_rectangle(box((172,112,426,352)),radius=28*scale,fill='#f7efdd')
d.rounded_rectangle(box((196,138,402,302)),radius=12*scale,fill='#102b24')
line([(220,252),(254,252),(254,212),(294,212),(294,236),(332,236),(332,182),(374,182)],'#a9d7b0',16)
line([(96,170),(132,170),(132,264),(170,264)],'#d6ad6d',20)
line([(96,366),(276,366),(276,352)],'#d6ad6d',20)
for x,y in [(96,170),(96,366)]:d.ellipse(box((x-20,y-20,x+20,y+20)),fill='#f7efdd')
d.ellipse(box((292,321,308,337)),fill='#23483d')
im=im.resize((512,512),Image.Resampling.LANCZOS)
im.save(ROOT/'workbench.png');im.save(ROOT/'workbench.ico',sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])
