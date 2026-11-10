"""Run local Windows tests; stop on the first failed subprocess."""
import subprocess
import sys
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def main():
    # Local HTTP tests should not depend on a machine's proxy configuration.
    os.environ['NO_PROXY']=os.environ['no_proxy']='127.0.0.1,localhost'
    for test in sorted((ROOT / 'tests').glob('*.test.mjs')):
        subprocess.run(['node', str(test)], cwd=ROOT, check=True)
    for name in ('test_global_library.py', 'test_keil_scan.py',
                 'test_project_store.py', 'test_storage.py', 'test_oled_link.py', 'test_suite_control.py', 'test_public_build.py', 'test_mcp.py'):
        subprocess.run([sys.executable, '-X', 'utf8', str(ROOT / 'tests' / name)],
                       cwd=ROOT, check=True)
    print('PASS all automated checks; no firmware compiled or flashed')

if __name__ == '__main__':
    main()
