"""Local wiring workbench; bounded project storage, no firmware access."""
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
import webbrowser,sys,json,secrets,threading,os,tempfile,re
ROOT=Path(__file__).resolve().parent/'web'
DATA=ROOT.parent/'projects'
import project_store
TOKEN=secrets.token_urlsafe(24)
LOCK=threading.Lock()
def path_for(name):
    if not isinstance(name,str) or not re.fullmatch(r'[a-zA-Z0-9_-]{1,70}',name):raise ValueError('无效项目编号')
    DATA.mkdir(exist_ok=True)
    p=DATA/(name+'.json')
    if p.resolve().parent!=DATA.resolve():raise ValueError('无效项目路径')
    return p
class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*a,**kw):super().__init__(*a,directory=str(ROOT),**kw)
    def log_message(self,*a):pass
    def reply(self,data,status=200):
        b=json.dumps(data,ensure_ascii=False).encode();self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8');self.end_headers();self.wfile.write(b)
    def authorized(self):return self.headers.get('X-Wiring-Token')==TOKEN and self.headers.get('Origin') in (None,f'http://127.0.0.1:{self.server.server_port}')
    def do_GET(self):
        from urllib.parse import urlparse,parse_qs
        url=urlparse(self.path)
        if url.path.startswith('/api/'):
            if not self.authorized():return self.reply({'error':'未授权'},403)
            try:
                if url.path=='/api/library':
                    from global_library import read_library
                    return self.reply(read_library())
                if url.path=='/api/projects':return self.reply(project_store.listing(DATA))
                if url.path=='/api/project':return self.reply(project_store.read(parse_qs(url.query)['id'][0],DATA))
                if url.path=='/api/history':return self.reply(project_store.checkpoints(parse_qs(url.query)['id'][0],DATA))
                return self.reply({'error':'未找到'},404)
            except (ValueError,OSError,KeyError) as e:return self.reply({'error':str(e)},400)
        if url.path in ('/','/index.html'):
            b=(ROOT/'index.html').read_text(encoding='utf-8').replace('__TOKEN__',TOKEN).encode();self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.end_headers();self.wfile.write(b);return
        if url.path not in ('/style.css','/app.mjs','/model.mjs','/persistence.mjs','/checks.mjs','/keil.mjs','/network_view.mjs'):self.send_error(404);return
        super().do_GET()
    def do_POST(self):
        if not self.authorized():return self.reply({'error':'未授权'},403)
        try:
            if self.path in ('/api/library/seed','/api/library/publish'):
                length=int(self.headers.get('Content-Length','0'))
                if not 0<length<=2000000:raise ValueError('模块库请求过大')
                data=json.loads(self.rfile.read(length))
                from global_library import seed,publish,Conflict
                try:
                    result=seed(data['modules']) if self.path.endswith('/seed') else publish(data['module'],data['expected_revision'],data['base_version'])
                except Conflict as e:return self.reply({'error':str(e)},409)
                return self.reply(result)
            if self.path=='/api/keil/pick':
                try:
                    import tkinter as tk
                    from tkinter import filedialog
                    dialog=tk.Tk();dialog.withdraw();dialog.attributes('-topmost',True)
                    try:directory=filedialog.askdirectory(title='选择 Keil 工程目录（只读扫描）')
                    finally:dialog.destroy()
                except Exception as e:return self.reply({'error':'目录选择器不可用，请手动粘贴工程路径：'+str(e)},400)
                return self.reply({'directory':directory})
            if self.path=='/api/keil/scan':
                length=int(self.headers.get('Content-Length','0'))
                if not 0<length<=12000:raise ValueError('扫描请求过大')
                data=json.loads(self.rfile.read(length))
                from keil_scan import scan
                return self.reply(scan(data['path'],data.get('target') or None))
            if self.path not in ('/api/project','/api/checkpoint','/api/restore'):return self.reply({'error':'未找到'},404)
            length=int(self.headers.get('Content-Length','0'))
            if not 0<length<=4000000:raise ValueError('请求不能超过 4MB')
            x=json.loads(self.rfile.read(length))
            try:
                if self.path=='/api/project':result=project_store.write(x['id'],x['package'],x['expected_revision'],'web',data=DATA)
                elif self.path=='/api/checkpoint':result=project_store.create_checkpoint(x['id'],x['expected_revision'],x.get('label','网页手动恢复点'),DATA)
                else:result=project_store.restore(x['id'],x['checkpoint'],x['expected_revision'],'web',DATA)
            except project_store.Conflict as e:return self.reply({'error':str(e)},409)
            return self.reply(result)
        except (ValueError,OSError,KeyError,TypeError) as e:self.reply({'error':str(e)},400)
    def end_headers(self):
        self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');super().end_headers()
    extensions_map={**SimpleHTTPRequestHandler.extensions_map,'.mjs':'text/javascript'}
def main():
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    url=f'http://127.0.0.1:{server.server_port}/';print(url,flush=True)
    if '--no-browser' not in sys.argv:webbrowser.open(url)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()
if __name__=='__main__':main()
