import base64, io, json, secrets, sys, urllib.parse, webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import core, studio, exporter, change_requests as requests

ROOT=core.ROOT
TOKEN=secrets.token_urlsafe(24)

class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args): pass
    def reply(self,data,status=200,content_type='application/json; charset=utf-8'):
        if isinstance(data,(dict,list)): data=json.dumps(data,ensure_ascii=False).encode('utf-8')
        elif isinstance(data,str): data=data.encode('utf-8')
        self.send_response(status);self.send_header('Content-Type',content_type)
        self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff')
        self.end_headers();self.wfile.write(data)
    def allowed(self):
        return self.headers.get('X-OLED-Token')==TOKEN and self.headers.get('Origin') in (None,f'http://127.0.0.1:{self.server.server_port}')
    def body(self):
        n=int(self.headers.get('Content-Length','0'))
        if n<0 or n>2500000: raise ValueError('请求过大')
        return json.loads(self.rfile.read(n).decode('utf-8'))
    def do_GET(self):
        try:
            path=urllib.parse.urlparse(self.path).path
            if path=='/favicon.ico': return self.reply(b'',204,'image/x-icon')
            if path=='/studio': return self.reply((ROOT/'web/studio.html').read_text(encoding='utf-8').replace('__TOKEN__',TOKEN),content_type='text/html; charset=utf-8')
            if path=='/': return self.reply((ROOT/'web/index.html').read_text(encoding='utf-8').replace('__TOKEN__',TOKEN),content_type='text/html; charset=utf-8')
            if path in ('/app.js','/style.css','/studio.js','/studio-tools.js','/requests.js'):
                return self.reply((ROOT/('web'+path)).read_text(encoding='utf-8'),content_type='text/javascript; charset=utf-8' if path.endswith('.js') else 'text/css; charset=utf-8')
            if not self.allowed(): return self.reply({'error':'未授权'},403)
            if path=='/api/requests':
                q=urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
                return self.reply(requests.list_requests(q.get('name',[None])[0]))
            if path=='/api/request':
                q=urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
                return self.reply(requests.read(q['id'][0]))
            if path=='/api/draft':
                q=urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query);return self.reply(core.load(q.get('name',['default'])[0]))
            if path=='/api/export/file':
                q=urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query);return self.reply(exporter.read_file(q['name'][0],q['file'][0]),content_type='application/octet-stream')
            if path=='/api/default': return self.reply(core.defaults())
            if path=='/api/studio/new': return self.reply(studio.new())
            if path=='/api/studio/list': return self.reply([p.stem for p in core.DRAFTS.glob('*.json') if p.stem.startswith(('project_','preset_'))])
            self.reply({'error':'未找到'},404)
        except Exception as e:self.reply({'error':str(e)},400)
    def do_POST(self):
        try:
            if not self.allowed(): return self.reply({'error':'未授权'},403)
            data=self.body()
            if self.path=='/api/export/open-folder':
                import os
                name=data['name'];core.draft_path(name)
                folder=exporter.EXPORTS/name
                if folder.resolve().parent!=exporter.EXPORTS.resolve() or not (folder/'manifest.json').is_file():raise ValueError('无效导出目录')
                os.startfile(str(folder.resolve()))
                return self.reply({'opened':True})
            if self.path=='/api/studio/event': return self.reply(studio.run(data['draft'],data['event']))
            if self.path=='/api/studio/image': return self.reply(studio.convert_image(data))
            if self.path=='/api/studio/export': return self.reply(exporter.export(data['draft'],data['name']))
            if self.path=='/api/request/create': return self.reply(requests.create(data['name'],data['text'],data['expected_revision']))
            if self.path=='/api/request/apply': return self.reply(requests.apply(data['id']))
            if self.path=='/api/request/cancel': return self.reply(requests.mark(data['id'],'cancelled'))
            if self.path=='/api/save': return self.reply(core.save(data['name'],data['draft'],data['expected_revision']))
            if self.path=='/api/render':
                draft=core.validate(data['draft']);im,issues=core.render(draft);buf=io.BytesIO();im.save(buf,format='PNG')
                elements=[] if draft.get('version')==2 else [dict(e,display_text=core.element_text(e,draft['simulation'],draft['alternatives'])) for e in draft['pages'][draft['page']]]
                return self.reply({'png':base64.b64encode(buf.getvalue()).decode(),'issues':issues,'elements':elements,'source_changed':core.source_changed(draft)})
            self.reply({'error':'未找到'},404)
        except RuntimeError as e:self.reply({'error':str(e)},409)
        except Exception as e:self.reply({'error':str(e)},400)

def main():
    srv=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    url=f'http://127.0.0.1:{srv.server_port}/'
    print('OLED 编辑器：'+url,flush=True)
    if '--no-browser' not in sys.argv:webbrowser.open(url)
    try:srv.serve_forever()
    except KeyboardInterrupt:pass
    finally:srv.server_close()
if __name__=='__main__':main()
