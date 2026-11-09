"""Native Windows entry point; reuses the existing HTTP app and model."""
import argparse
import json
import logging
from pathlib import Path
import sys
import threading
import urllib.request

import global_library
import project_store
import server
import oled_link

ROOT = Path(__file__).resolve().parent

def configure(data_dir=None):
    base = Path(sys.executable).resolve().parent if getattr(sys, 'frozen', False) else ROOT
    data = Path(data_dir).resolve() if data_dir else base / ('data' if getattr(sys, 'frozen', False) else 'desktop_data')
    data.mkdir(parents=True, exist_ok=True)
    project_store.DATA = server.DATA = data / 'projects'
    global_library.STORE = data / 'module_library'
    oled_link.CONFIG = data / 'oled_link.json'
    node = ROOT / 'runtime/node.exe'
    project_store.NODE_EXECUTABLE = str(node) if node.exists() else None
    return data

def start_server():
    http = server.ThreadingHTTPServer(('127.0.0.1', 0), server.Handler)
    thread = threading.Thread(target=http.serve_forever, daemon=True)
    thread.start()
    return http, thread, f'http://127.0.0.1:{http.server_port}/'

def self_test(output):
    output = Path(output).resolve()
    configure(output.parent / 'desktop-test-data')
    package = json.loads((ROOT / 'examples/stm32-oled-buzzer.json').read_text(encoding='utf-8'))
    before = project_store.read('desktop_self_test')['revision'] if project_store.path_for('desktop_self_test').exists() else 0
    result = project_store.write('desktop_self_test', package, before)
    checks = project_store.engine('check', package=package)
    preview = project_store.engine('preview', package=package)
    assert '<svg' in preview['svg']
    assert project_store.read('desktop_self_test')['package'] == package
    http, thread, url = start_server()
    try:
        with urllib.request.urlopen(url) as response:
            assert '模块接线画布' in response.read().decode('utf-8')
        request = urllib.request.Request(url + 'api/project?id=desktop_self_test', headers={'X-Wiring-Token': server.TOKEN})
        with urllib.request.urlopen(request) as response:
            assert json.load(response)['revision'] == result['revision']
        with urllib.request.urlopen(url + 'network_view.mjs') as response:
            assert response.status == 200
    finally:
        http.shutdown(); http.server_close(); thread.join()
    output.write_text(json.dumps({'status':'passed','frozen':bool(getattr(sys,'frozen',False)),
        'bundled_node':project_store.NODE_EXECUTABLE,'checks':checks['count'],
        'validated':['packaged assets','Node model','save/reopen','SVG','HTTP API'],
        'not_validated':['GUI interactions','Keil compilation','hardware']}, ensure_ascii=False, indent=2), encoding='utf-8')

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data-dir')
    parser.add_argument('--self-test', metavar='REPORT_JSON')
    args = parser.parse_args()
    if args.self_test:
        self_test(args.self_test)
        return
    data = configure(args.data_dir)
    logging.basicConfig(filename=str(data / 'desktop.log'), encoding='utf-8', level=logging.WARNING)
    import webview
    http, thread, url = start_server()
    try:
        webview.settings['ALLOW_DOWNLOADS'] = True
        webview.create_window('接线工作台 · Wiring Workbench', url, width=1440, height=920,
            min_size=(1000, 680), confirm_close=True, background_color='#f5f0e6', text_select=True,
            localization={'global.quitConfirmation':'关闭接线工作台？请先保存当前图纸。'})
        webview.start(gui='edgechromium', private_mode=False, storage_path=str(data / 'webview'))
    finally:
        http.shutdown(); http.server_close(); thread.join()

if __name__ == '__main__':
    try:
        main()
    except Exception:
        logging.exception('Desktop startup failed')
        if '--self-test' not in sys.argv:
            import ctypes
            ctypes.windll.user32.MessageBoxW(None, '启动失败。请查看 data/desktop.log，并确认电脑已安装 Microsoft Edge WebView2 Runtime。', '接线工作台', 16)
        raise
