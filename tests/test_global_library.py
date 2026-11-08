import sys,unittest,tempfile,json,hashlib,threading
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import global_library as lib
class Tests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.original=lib.STORE;lib.STORE=Path(self.tmp.name)/'library'
  self.m={'id':'test-module','name':'测试模块','kind':'输入','pins':[{'id':'p1','name':'IN','side':'left','offset':50,'voltage':'未知','role':'未知'}]}
 def tearDown(self):lib.STORE=self.original;self.tmp.cleanup()
 def test_persistent_seed(self):
  first=lib.seed([self.m]);self.assertEqual(first['revision'],1);self.assertEqual(lib.read_library(),first);self.assertEqual(lib.seed([{**self.m,'name':'不能替换'}]),first)
 def test_versions_and_conflict(self):
  lib.seed([self.m]);r=lib.publish({**self.m,'name':'新版'},1,1);self.assertEqual(r['modules'][0]['version'],2);self.assertEqual(len(r['history'][self.m['id']]),2)
  with self.assertRaises(lib.Conflict):lib.publish(self.m,1,1)
  with self.assertRaises(lib.Conflict):lib.publish(self.m,2,1)
  raw=json.loads((lib.STORE/'library.json').read_text(encoding='utf-8'));self.assertEqual(raw['templates'][self.m['id']][0]['name'],'测试模块')
 def test_project_untouched(self):
  project=Path(self.tmp.name)/'old.json';project.write_text(json.dumps({'library':[self.m]}));before=project.read_bytes();lib.seed([self.m]);lib.publish({**self.m,'name':'new'},1,1);self.assertEqual(project.read_bytes(),before)
 def test_invalid_data_and_no_instance_metadata(self):
  with self.assertRaises(ValueError):lib.seed([{**self.m,'pins':[]}])
  with self.assertRaises(ValueError):lib.template({**self.m,'pins':[self.m['pins'][0],self.m['pins'][0]]})
  lib.seed([self.m]);r=lib.publish({**self.m,'id':'copy','x':900,'templateId':'leak'},1,0);t=next(x for x in r['modules'] if x['id']=='copy');self.assertNotIn('x',t);self.assertNotIn('templateId',t)
 def test_concurrent_publication(self):
  lib.seed([self.m]);results=[]
  def save():
   try:lib.publish(self.m,1,1);results.append('ok')
   except lib.Conflict:results.append('conflict')
  a=threading.Thread(target=save);b=threading.Thread(target=save);a.start();b.start();a.join();b.join();self.assertCountEqual(results,['ok','conflict'])
if __name__=='__main__':unittest.main(verbosity=2)
