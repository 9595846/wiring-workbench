import importlib.util,json,threading,tempfile,urllib.request,urllib.error,unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
spec=importlib.util.spec_from_file_location('workbench',Path(__file__).resolve().parents[1]/'server.py');app=importlib.util.module_from_spec(spec);spec.loader.exec_module(app)
class Tests(unittest.TestCase):
 def test_storage(self):
  with tempfile.TemporaryDirectory() as tmp:
   app.DATA=Path(tmp);srv=app.ThreadingHTTPServer(('127.0.0.1',0),app.Handler);thread=threading.Thread(target=srv.serve_forever,daemon=True);thread.start();base=f'http://127.0.0.1:{srv.server_port}'
   def call(path,body=None,token=app.TOKEN):
    req=urllib.request.Request(base+path,data=json.dumps(body).encode() if body is not None else None,headers={'Content-Type':'application/json','X-Wiring-Token':token})
    with urllib.request.urlopen(req) as response:return json.load(response)
   try:
    with self.assertRaises(urllib.error.HTTPError) as error:call('/api/projects',token='wrong')
    self.assertEqual(error.exception.code,403);error.exception.close()
    pkg={'format':'wiring-workbench','version':1,'doc':{'version':1,'title':'测试','modules':[],'wires':[],'nodes':[],'annotations':[]},'library':[]};body={'id':'test','package':pkg,'expected_revision':0}
    self.assertEqual(call('/api/project',body)['revision'],1)
    self.assertEqual(call('/api/project?id=test')['package'],pkg)
    with self.assertRaises(urllib.error.HTTPError) as error:call('/api/project',body)
    self.assertEqual(error.exception.code,409);error.exception.close()
    with self.assertRaises(urllib.error.HTTPError) as error:call('/api/project',{**body,'id':'../outside'})
    error.exception.close()
    self.assertEqual(len(call('/api/projects')),1)
   finally:srv.shutdown();srv.server_close();thread.join()
if __name__=='__main__':unittest.main()
