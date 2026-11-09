import json, tempfile, sys, threading, unittest
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import oled_link as link

class FakeOLED(BaseHTTPRequestHandler):
 def log_message(self,*a):pass
 def do_GET(self):
  if self.path=='/studio':out=b'<script>window.OLED_TOKEN="test";</script>'
  else:
   assert self.headers.get('X-OLED-Token')=='test'
   out=json.dumps({'version':2,'revision':3,'page':0,'pages':[{'name':'测试页'}]}).encode()
  self.send_response(200);self.end_headers();self.wfile.write(out)
 def do_POST(self):
  assert self.headers.get('X-OLED-Token')=='test'
  self.rfile.read(int(self.headers['Content-Length']))
  self.send_response(200);self.end_headers();self.wfile.write(b'{"png":"image","issues":[]}')

class Tests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
  for p in ('web','drafts','desktop_logs'):(self.root/p).mkdir()
  (self.root/'web/studio.html').write_text('test')
  self.exe=self.root/'OLEDWorkbench.exe';self.exe.write_bytes(b'placeholder')
  self.design=self.root/'drafts/project_test.json'
  self.design.write_text(json.dumps({'version':2,'revision':3,'pages':[{'name':'测试'}]}))
  self.original=link.CONFIG;link.CONFIG=self.root/'config.json'
  link.CONFIG.write_text(json.dumps({'workspace':str(self.root),'executable':str(self.exe)}))
  self.http=ThreadingHTTPServer(('127.0.0.1',0),FakeOLED);self.thread=threading.Thread(target=self.http.serve_forever,daemon=True);self.thread.start()
  self.session={'workspace':str(self.root),'url':f'http://127.0.0.1:{self.http.server_port}/studio'}
  self.write_session()
 def write_session(self):(self.root/'desktop_logs/integration-session.json').write_text(json.dumps(self.session))
 def tearDown(self):
  self.http.shutdown();self.http.server_close();self.thread.join();link.CONFIG=self.original;self.tmp.cleanup()
 def test_list_preview_and_no_write(self):
  before=self.design.read_bytes();self.assertEqual(link.listing()['projects'][0]['revision'],3)
  self.assertTrue(link.preview('project_test',expected_revision=2)['changed'])
  self.assertFalse(link.preview('project_test',expected_revision=3)['changed'])
  self.assertEqual(before,self.design.read_bytes())
 def test_reject_missing_path_page_and_remote_session(self):
  for name in ('../project_test','project_missing'):
   with self.assertRaises(ValueError):link.preview(name)
  with self.assertRaises(ValueError):link.preview('project_test',page=9)
  self.session['url']='https://example.com/studio';self.write_session()
  with self.assertRaises(ValueError):link.preview('project_test')
 def test_launch_only_configured_exe_and_revision(self):
  with patch.object(link.subprocess,'Popen') as popen:
   with self.assertRaises(ValueError):link.launch('project_test',expected_revision=2)
   popen.assert_not_called();link.launch('project_test',expected_revision=3)
   self.assertEqual(popen.call_args.args[0],[str(self.exe.resolve()),'--project','project_test'])
 def test_relative_paths_are_based_on_config_location(self):
  link.CONFIG.write_text(json.dumps({'workspace':'.','executable':'OLEDWorkbench.exe'}))
  self.assertEqual(link.config(),(self.exe.resolve(),self.root.resolve()))

if __name__=='__main__':unittest.main(verbosity=2)
