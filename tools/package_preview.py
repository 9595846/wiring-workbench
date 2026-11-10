"""Validate a relocated frozen suite with no Python/Node on PATH, then ZIP it."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import zipfile

def validate_and_package(suite, output, version):
    suite=suite.resolve();output=output.resolve()
    manifest=json.loads((suite/'suite-manifest.json').read_text('utf-8'))
    if not manifest.get('public_build'):raise ValueError('Only public builds may be packaged')
    for relative in ('WiringWorkbench/data/projects','WiringWorkbench/data/module_library',
                     'oled_workspace/drafts','oled_workspace/requests','oled_workspace/exports',
                     'oled_workspace/integration_history','oled_workspace/desktop_logs'):
        if (suite/relative).exists() and any((suite/relative).iterdir()):
            raise ValueError('User/test data in public package: '+relative)
    for file in suite.rglob('*'):
        if file.is_file() and (file.suffix in ('.log','.lock','.tmp') or file.name.startswith('.env')):
            raise ValueError('Unexpected local file: '+str(file.relative_to(suite)))
    env=os.environ.copy()
    env['PATH']=str(Path(os.environ['SystemRoot'])/'System32')+';'+os.environ['SystemRoot']
    for name in ('PYTHONPATH','PYTHONHOME','OLED_WORKBENCH_ROOT','OLED_WORKBENCH_FIRMWARE'):
        env.pop(name,None)
    env['NO_PROXY']=env['no_proxy']='127.0.0.1,localhost'
    with tempfile.TemporaryDirectory(prefix='workbench-release-') as tmp:
        relocated=Path(tmp)/'中文 空格 Suite'
        shutil.copytree(suite,relocated)
        wire_report=Path(tmp)/'wiring.json'
        subprocess.run([str(relocated/'WiringWorkbench/WiringWorkbench.exe'),'--self-test',str(wire_report)],
                       cwd=relocated,env=env,check=True,timeout=120)
        wire=json.loads(wire_report.read_text('utf-8'))
        assert wire['status']=='passed' and wire['frozen']
        # Windows runner TEMP may use an 8.3 alias while the EXE resolves the
        # long path. Compare file identity, not the textual path prefix.
        expected_node=relocated/'WiringWorkbench/_internal/runtime/node.exe'
        assert Path(wire['bundled_node']).samefile(expected_node), 'Self-test did not use the packaged Node executable'
        subprocess.run([str(relocated/'OLEDWorkbench/OLEDWorkbench.exe'),'--smoke-test'],
                       cwd=relocated,env=env,check=True,timeout=120)
        oled=json.loads((relocated/'oled_workspace/desktop_logs/last_run.json').read_text('utf-8'))
        assert oled['http_and_profile']=='passed' and oled['data_and_export']=='passed' and oled['server_stopped']
        report={'version':version,'status':'passed','path_without_python_node':True,
                'relocated_unicode_directory':True,'wiring':wire['validated'],'oled':oled['validated'],
                'not_validated':['Full native GUI interactions','Separate physical PC','Keil compile','Physical OLED/hardware'],
                'environment':'GitHub Windows hosted runner' if os.environ.get('GITHUB_ACTIONS') else 'Author Windows computer',
                'source_commit':os.environ.get('GITHUB_SHA','local working tree')}
    (suite/'VALIDATION.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    output.mkdir(parents=True,exist_ok=True)
    archive=output/('WorkbenchSuite-'+version+'-windows-x64.zip')
    if archive.exists():raise ValueError('Archive already exists')
    with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for file in sorted(suite.rglob('*')):
            if file.is_file():z.write(file,Path('WorkbenchSuite')/file.relative_to(suite))
    digest=hashlib.sha256(archive.read_bytes()).hexdigest()
    (output/'SHA256SUMS.txt').write_text(digest+'  '+archive.name+'\n',encoding='ascii')
    print(json.dumps({'archive':str(archive),'sha256':digest,'bytes':archive.stat().st_size,'validation':report},ensure_ascii=False))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('suite',type=Path)
    parser.add_argument('--output',type=Path,default=Path('dist/releases'))
    parser.add_argument('--version',required=True)
    args=parser.parse_args()
    if not all(c.isalnum() or c in '.-' for c in args.version):raise ValueError('Invalid version')
    validate_and_package(args.suite,args.output,args.version)
