"""Build a directory-based Windows executable with embedded Python and Node."""
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def main():
    node = shutil.which('node')
    if not node:
        raise SystemExit('Node.js must be installed on the build machine')
    args = [sys.executable, '-m', 'PyInstaller', '--noconfirm', '--windowed', '--onedir',
            '--name', 'WiringWorkbench', '--distpath', str(ROOT / 'dist'),
            '--workpath', str(ROOT / 'build'), '--specpath', str(ROOT / 'build'),
            '--add-binary', node + ';runtime', '--collect-all', 'webview']
    for item in ('web','examples','bridge.mjs','THIRD_PARTY_NOTICES.md'):
        args += ['--add-data', str(ROOT / item) + ';' + (item if (ROOT / item).is_dir() else '.')]
    args.append(str(ROOT / 'desktop.py'))
    destination = ROOT / 'dist/WiringWorkbench'
    # PyInstaller replaces the entire output folder. Preserve portable user data
    # outside that folder before a rebuild, including on a failed build.
    backup = ROOT / 'build' / ('desktop-data-' + uuid.uuid4().hex)
    if (destination/'data').exists():
        shutil.copytree(destination/'data', backup)
    try:
        subprocess.run(args, cwd=ROOT, check=True)
    finally:
        if backup.exists():
            shutil.copytree(backup, destination/'data', dirs_exist_ok=True)
    config = ROOT / 'oled_link.local.json'
    if config.exists():
        (destination/'data').mkdir(exist_ok=True)
        if not (destination/'data/oled_link.json').exists():
            shutil.copy2(config,destination/'data/oled_link.json')
    shutil.copy2(ROOT / 'docs/DESKTOP.md', destination / '使用说明.txt')
    notices = ROOT / 'desktop_notices'
    if notices.exists():
        shutil.copytree(notices, destination / 'licenses', dirs_exist_ok=True)
    print(destination / 'WiringWorkbench.exe')

if __name__ == '__main__':
    main()
