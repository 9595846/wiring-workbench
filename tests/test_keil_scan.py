import sys,unittest,tempfile,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from keil_scan import parse_source,scan
class Tests(unittest.TestCase):
 def test_std_and_evidence(self):
  source='#define SCL GPIO_Pin_10\n#define SDA GPIO_Pin_11\nvoid init(void){\ng.GPIO_Pin=SCL|SDA;g.GPIO_Mode=GPIO_Mode_Out_OD;\nGPIO_Init(GPIOB,&g);\n}'
  r,u=parse_source(source,'display.c');self.assertEqual([(e['pin'],e['symbols']) for e in r],[('PB10',['SCL']),('PB11',['SDA'])]);self.assertEqual(r[0]['line'],5);self.assertEqual(r[0]['macros'][0]['line'],1)
 def test_hal_alias(self):
  r,_=parse_source('#define PORT GPIOA\n#define LED GPIO_PIN_5\nvoid f(){s.Pin=LED;s.Mode=GPIO_MODE_OUTPUT_PP;HAL_GPIO_Init(PORT,&s);}','x.c');self.assertEqual(r[0]['pin'],'PA5')
 def test_comments_dynamic_and_scopes(self):
  r,u=parse_source('// GPIO_Init(GPIOA,&s);\nvoid f(){s.GPIO_Pin=calc();GPIO_Init(GPIOB,&s);}\nvoid g(){GPIO_Init(GPIOA,&s);}','x.c');self.assertEqual(r,[]);self.assertEqual(len(u),2)
 def test_condition_and_duplicate_macro(self):
  r,_=parse_source('#ifdef X\n#define P GPIO_Pin_1\nvoid f(){s.GPIO_Pin=P;GPIO_Init(GPIOA,&s);}\n#endif','x.c');self.assertTrue(r[0]['conditional'])
  r,u=parse_source('#define P GPIO_Pin_1\n#define P GPIO_Pin_2\nvoid f(){s.GPIO_Pin=P;GPIO_Init(GPIOA,&s);}','x.c');self.assertFalse(r);self.assertTrue(u)
 def test_target_scope_excluded_and_external(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);(root/'ok.c').write_text('void f(){s.GPIO_Pin=GPIO_Pin_2;GPIO_Init(GPIOA,&s);}')
   (root/'off.c').write_text('void f(){s.GPIO_Pin=GPIO_Pin_7;GPIO_Init(GPIOA,&s);}')
   def target(name):return f'<Target><TargetName>{name}</TargetName><TargetOption><Device>STM32F103C8</Device></TargetOption><Groups><Group><Files><File><FilePath>ok.c</FilePath></File><File><FilePath>off.c</FilePath><FileOption><CommonProperty><IncludeInBuild>0</IncludeInBuild></CommonProperty></FileOption></File><File><FilePath>../outside.c</FilePath></File></Files></Group></Groups></Target>'
   p=root/'Test.uvprojx';p.write_text('<Project><Targets>'+target('A')+target('B')+'</Targets></Project>');r=scan(str(p));self.assertTrue(r['needs_target']);r=scan(str(p),'A');self.assertEqual([e['pin'] for e in r['evidence']],['PA2']);self.assertEqual(len(r['skipped']),2)
 def test_invalid_xml(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/'bad.uvprojx';p.write_text('<broken>')
   with self.assertRaises(ValueError):scan(str(p))
 def test_current_project_read_only(self):
  root=Path(__file__).resolve().parent/'fixtures/keil';files=[p for p in root.rglob('*') if p.is_file() and p.suffix.lower() in ('.c','.h','.uvprojx')];before={p:hashlib.sha256(p.read_bytes()).digest() for p in files};r=scan(str(root/'Project.uvprojx'));e=[e for e in r['evidence'] if e['file']=='Hardware/display.c'];self.assertEqual({e['pin'] for e in e},{'PB10','PB11'});self.assertEqual(before,{p:hashlib.sha256(p.read_bytes()).digest() for p in files})
if __name__=='__main__':unittest.main(verbosity=2)
