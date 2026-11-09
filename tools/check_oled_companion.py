"""Check the vendored suite companion without any external firmware workspace."""
import os
import sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]/'oled_companion'
os.environ['OLED_WORKBENCH_ROOT']=str(root)
os.environ['OLED_WORKBENCH_FIRMWARE']=str(root/'firmware_baseline')
sys.path.insert(0,str(root))
import core,studio,exporter
draft=studio.new();draft['pages'][0]['elements'][0]['text']='READY'
image,issues=core.render(draft)
assert image.size==(128,64)
assert exporter.profile()['device']=='STM32F103C8'
generated=exporter.generate(draft)
assert generated
print('PASS standalone OLED companion render and adapter generation; no firmware modified')
