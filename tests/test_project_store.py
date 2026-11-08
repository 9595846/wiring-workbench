import sys,tempfile,unittest,copy
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import project_store as store
class Tests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.old=store.DATA;store.DATA=Path(self.tmp.name)
  self.pkg=store.engine('new',title='测试',library=[]);self.initial=store.write('test',self.pkg,0)
 def tearDown(self):store.DATA=self.old;self.tmp.cleanup()
 def test_atomic_edit_and_restore(self):
  cp=store.create_checkpoint('test',1);result=store.edit('test',[{'type':'rename_project','title':'新图纸'},{'type':'add_custom_module','name':'模块','pins':['IN','GND']}],1);self.assertEqual(result['revision'],2);self.assertEqual(len(result['package']['doc']['modules']),1);self.assertTrue(result['checkpoint']);r=store.restore('test',cp['id'],2);self.assertEqual(r['revision'],3);self.assertEqual(r['package'],self.pkg);self.assertGreaterEqual(len(store.checkpoints('test')),3)
 def test_failed_batch_does_not_save(self):
  with self.assertRaises(ValueError):store.edit('test',[{'type':'rename_project','title':'不应保存'},{'type':'move_module','id':'missing','x':0,'y':0}],1)
  self.assertEqual(store.read('test'),{'revision':1,'package':self.pkg})
 def test_stale_revision_no_history_write(self):
  store.edit('test',[{'type':'rename_project','title':'新图纸'}],1);count=len(store.checkpoints('test'))
  with self.assertRaises(store.Conflict):store.write('test',self.pkg,1)
  self.assertEqual(len(store.checkpoints('test')),count)
 def test_invalid_paths_and_package(self):
  with self.assertRaises(ValueError):store.read('../outside')
  with self.assertRaises(ValueError):store.restore('test','../x',1)
  bad=copy.deepcopy(self.pkg);bad['doc']['wires']=[{'id':'bad'}]
  with self.assertRaises(ValueError):store.write('test',bad,1)
 def test_checkpoint_tamper(self):
  cp=store.create_checkpoint('test',1);p=store.history_dir('test')/(cp['id']+'.json');s=p.read_text(encoding='utf-8').replace('测试','篡改');p.write_text(s,encoding='utf-8')
  with self.assertRaises(ValueError):store.restore('test',cp['id'],1)
 def test_check_and_svg(self):
  self.assertIn('issues',store.engine('check',package=self.pkg));svg=store.engine('preview',package=self.pkg)['svg'];self.assertIn('<svg',svg)
 def test_power_display_edit(self):
  r=store.edit('test',[{'type':'set_power_display','mode':'compact'}],1)
  expected=copy.deepcopy(self.pkg);expected['doc']['powerDisplay']='compact'
  self.assertEqual(r['package'],expected);self.assertEqual(r['revision'],2)
  with self.assertRaises(ValueError):store.edit('test',[{'type':'set_power_display','mode':'bad'}],2)
  self.assertEqual(store.read('test')['package'],expected)
if __name__=='__main__':unittest.main(verbosity=2)
