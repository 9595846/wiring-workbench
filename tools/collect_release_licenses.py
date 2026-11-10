"""Collect installed distribution notices and exact runtime licenses for a release."""
import importlib.metadata as metadata
import json
from pathlib import Path
import shutil
import subprocess
import sys
import urllib.request


def collect(destination, node):
    destination.mkdir(parents=True, exist_ok=True)
    inventory = []
    for dist in metadata.distributions():
        name = dist.metadata['Name']
        copied = []
        for entry in dist.files or []:
            path = Path(str(entry))
            if any(word in path.name.lower() for word in ('license', 'copying', 'notice', 'authors')):
                source = Path(dist.locate_file(entry))
                if source.is_file() and source.suffix.lower() not in ('.py', '.pyc', '.exe', '.dll'):
                    target = destination / 'python-packages' / (name+'-'+dist.version) / path.name
                    # Keep directory context to avoid colliding bundled library notices.
                    target = target.parent / str(entry).replace('/', '_').replace('\\', '_').replace('..', '_')
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, target)
                    copied.append(str(target.relative_to(destination)))
        inventory.append({'name': name, 'version': dist.version, 'notices': copied,
                          'license_metadata': dist.metadata.get('License-Expression') or dist.metadata.get('License')})
    python_license = Path(sys.base_prefix) / 'LICENSE.txt'
    if not python_license.exists():
        raise RuntimeError('Python LICENSE.txt is required for distribution')
    shutil.copy2(python_license, destination/'Python-LICENSE.txt')
    version = subprocess.check_output([str(node), '--version'], text=True).strip()
    # Node's source LICENSE includes notices for its bundled components.
    with urllib.request.urlopen('https://raw.githubusercontent.com/nodejs/node/'+version+'/LICENSE', timeout=60) as response:
        license_text = response.read()
    if b'Copyright' not in license_text or len(license_text) < 1000:
        raise RuntimeError('Unexpected Node license response')
    (destination/'Node-LICENSE.txt').write_bytes(license_text)
    (destination/'BUILD_DEPENDENCIES.json').write_text(json.dumps({
        'python':sys.version.split()[0], 'node':version,
        'note':'Build environment inventory; not every package is bundled in the executable.',
        'packages':inventory},ensure_ascii=False,indent=2),encoding='utf-8')
    for required in ('pywebview','pythonnet','clr_loader','pillow','pyinstaller'):
        if not any(d['name'].lower().replace('-','_') == required and d['notices'] for d in inventory):
            raise RuntimeError('Missing required distribution notice: '+required)

