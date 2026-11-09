"""Native desktop entry, sharing the existing workspace with the web editor and MCP."""
import argparse
import json
import os
from pathlib import Path
import sys
import threading
import urllib.request
import urllib.parse
import re

def workspace():
    entry = Path(sys.executable if getattr(sys, 'frozen', False) else __file__).resolve()
    config = entry.parent / 'workspace.json'
    if config.is_file():
        settings=json.loads(config.read_text(encoding='utf-8'))
        configured=Path(settings['workspace'])
        root=(configured if configured.is_absolute() else config.parent/configured).resolve()
        if settings.get('firmware_baseline'):
            baseline=Path(settings['firmware_baseline'])
            baseline=(baseline if baseline.is_absolute() else config.parent/baseline).resolve()
            os.environ['OLED_WORKBENCH_FIRMWARE']=str(baseline)
        if (root / 'web/studio.html').is_file() and (root / 'export_profile.json').is_file():
            return root
        raise RuntimeError('workspace.json 中的工作台目录无效')
    for parent in entry.parents:
        if (parent / 'web/studio.html').is_file() and (parent / 'export_profile.json').is_file():
            return parent
    raise RuntimeError('找不到工作台目录，请在 EXE 旁放置 workspace.json 指定 workspace 路径')

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--smoke-test', action='store_true')
    parser.add_argument('--window-test', action='store_true')
    parser.add_argument('--project', help='Open a saved project without changing it')
    args = parser.parse_args()
    root = workspace()
    if args.project and (not re.fullmatch(r'project_[A-Za-z0-9_-]{1,32}', args.project) or not (root/'drafts'/(args.project+'.json')).is_file()):
        raise ValueError('联动项目不存在或名称无效')
    os.environ['OLED_WORKBENCH_ROOT'] = str(root)
    logs = root / 'desktop_logs'
    logs.mkdir(exist_ok=True)
    if sys.stdout is None: sys.stdout = (logs / 'stdout.log').open('a', encoding='utf-8')
    if sys.stderr is None: sys.stderr = (logs / 'stderr.log').open('a', encoding='utf-8')
    import server
    from http.server import ThreadingHTTPServer
    srv = ThreadingHTTPServer(('127.0.0.1', 0), server.Handler)
    worker = threading.Thread(target=srv.serve_forever, daemon=True)
    worker.start()
    url = f'http://127.0.0.1:{srv.server_port}/studio'
    if args.project:
        url += '?project=' + urllib.parse.quote(args.project)
    session_path = logs / 'integration-session.json'
    session_tmp = logs / ('integration-session-'+str(os.getpid())+'.tmp')
    session_tmp.write_text(json.dumps({'pid':os.getpid(),'workspace':str(root),'url':url},ensure_ascii=False),encoding='utf-8')
    os.replace(session_tmp, session_path)
    report = {'workspace': str(root), 'url': url, 'window_loaded': False, 'server_stopped': False}
    try:
        if args.smoke_test:
            html = urllib.request.urlopen(url).read().decode('utf-8')
            assert '/requests.js' in html and 'modeBadge' in html
            for name in ('studio.js', 'studio-tools.js', 'requests.js'):
                assert urllib.request.urlopen(url.rsplit('/', 1)[0] + '/' + name).status == 200
            import exporter
            exporter.profile()
            report['http_and_profile'] = 'passed'
        else:
            import webview
            webview.settings['ALLOW_DOWNLOADS'] = True
            window = webview.create_window('OLED 工作台', url, width=1400, height=920,
                                           min_size=(900, 640), confirm_close=True,
                                           localization={'global.quitConfirmation':'关闭 OLED 工作台？请先保存当前设计。'})
            def loaded():
                report['window_loaded'] = True
                if args.window_test:
                    def finish():
                        report['title'] = window.evaluate_js('document.title')
                        report['request_panel'] = window.evaluate_js("!!document.getElementById('requestPanel')")
                        window.destroy()
                    timer = threading.Timer(2, finish)
                    timer.daemon = True
                    timer.start()
            window.events.loaded += loaded
            webview.start(gui='edgechromium', private_mode=False,
                          storage_path=str(logs / 'webview'))
    finally:
        srv.shutdown()
        srv.server_close()
        worker.join(timeout=3)
        report['server_stopped'] = not worker.is_alive()
        try:
            if json.loads(session_path.read_text(encoding='utf-8'))['pid'] == os.getpid(): session_path.unlink()
        except (OSError,ValueError,KeyError): pass
        (logs / 'last_run.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    if args.window_test and not report['window_loaded']:
        raise RuntimeError('桌面窗口未成功加载')

if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, str(exc), 'OLED 工作台启动失败', 0x10)
        raise
