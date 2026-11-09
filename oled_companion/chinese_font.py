"""Optional local Chinese design font; never a claim about firmware glyph coverage."""
import os
from functools import lru_cache
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont

@lru_cache(maxsize=1)
def font():
    path=Path(os.environ.get('WINDIR','C:/Windows'))/'Fonts/simsun.ttc'
    return ImageFont.truetype(str(path),12)

@lru_cache(maxsize=4096)
def rows(char):
    # Restrict supplement to common CJK and punctuation. Unsupported symbols stay explicit.
    cp=ord(char)
    if not (0x3400<=cp<=0x9fff or 0x3000<=cp<=0x303f or 0xff00<=cp<=0xffef):return None
    f=font();mask=f.getmask(char)
    if bytes(mask)==bytes(f.getmask(chr(0x10ffff))):return None
    tile=Image.new('L',(12,12));ImageDraw.Draw(tile).text((0,0),char,font=f,fill=255,anchor='lt')
    return [sum(0x8000>>x for x in range(12) if tile.getpixel((x,y))>=96) for y in range(12)]
