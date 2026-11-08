"""Run local Windows tests; stop on the first failed subprocess."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def main():
    for test in sorted((ROOT / 'tests').glob('*.test.mjs')):
        subprocess.run(['node', str(test)], cwd=ROOT, check=True)
    for name in ('test_global_library.py', 'test_keil_scan.py',
                 'test_project_store.py', 'test_storage.py', 'test_mcp.py'):
        subprocess.run([sys.executable, '-X', 'utf8', str(ROOT / 'tests' / name)],
                       cwd=ROOT, check=True)
    print('PASS all automated checks; no firmware compiled or flashed')

if __name__ == '__main__':
    main()
