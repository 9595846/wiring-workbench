"""Build an isolated portable suite without replacing the original applications."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import argparse

ROOT=Path(__file__).resolve().parents[1]
WORKSPACE=ROOT.parent
OLED=ROOT/'oled_companion' if (ROOT/'oled_companion').exists() else WORKSPACE/'oled_preview'
STAGE=ROOT/'build/suite'
DEST=ROOT/'dist/WorkbenchSuite'

def build(name,entry,python,extra=()):
    args=[str(python),'-m','PyInstaller','--noconfirm','--windowed','--onedir',
        '--name',name,'--distpath',str(STAGE/'apps'),'--workpath',str(STAGE/'cache'/name),
        '--specpath',str(STAGE/'specs'),'--paths',str(entry.parent),*extra,str(entry)]
    subprocess.run(args,cwd=entry.parent,check=True)

def copy_missing(source,destination):
    if not source.exists():return
    for p in source.rglob('*'):
        if p.is_file() and not p.name.endswith(('.lock','.tmp')):
            target=destination/p.relative_to(source)
            if not target.exists():target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)

def main():
    global DEST
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path)
    options=parser.parse_args()
    if options.output:DEST=options.output.resolve()
    STAGE.mkdir(parents=True,exist_ok=True);DEST.mkdir(parents=True,exist_ok=True)
    python=ROOT/'.venv/Scripts/python.exe'
    node=shutil.which('node')
    if not node:raise SystemExit('Node required on build machine')
    extra=['--collect-all','webview','--add-binary',node+';runtime']
    for item in ('web','examples','bridge.mjs','THIRD_PARTY_NOTICES.md'):
        extra+=['--add-data',str(ROOT/item)+';'+(item if (ROOT/item).is_dir() else '.')]
    build('WiringWorkbench',ROOT/'desktop.py',python,extra)
    oled_python=OLED/'.desktop-venv/Scripts/python.exe'
    build('OLEDWorkbench',OLED/'desktop.py',oled_python if oled_python.exists() else python,
          ['--collect-all','webview','--collect-all','pythonnet','--hidden-import','webview.platforms.winforms'])
    build('WorkbenchSuite',ROOT/'suite_launcher.py',python,['--contents-directory','_launcher',
          '--icon',str(ROOT/'assets/launcher/workbench.ico'),
          '--add-data',str(ROOT/'assets/launcher')+';assets/launcher'])
    for name in ('WiringWorkbench','OLEDWorkbench'):
        shutil.copytree(STAGE/'apps'/name,DEST/name,dirs_exist_ok=True)
    launcher=STAGE/'apps/WorkbenchSuite'
    shutil.copy2(launcher/'WorkbenchSuite.exe',DEST/'WorkbenchSuite.exe')
    shutil.copytree(launcher/'_launcher',DEST/'_launcher',dirs_exist_ok=True)
    # Independent user data: initial snapshots only, never overwrite on a rebuild.
    copy_missing(ROOT/'dist/WiringWorkbench/data/projects',DEST/'WiringWorkbench/data/projects')
    copy_missing(ROOT/'dist/WiringWorkbench/data/module_library',DEST/'WiringWorkbench/data/module_library')
    for name in ('web','fonts','export_runtime'):
        shutil.copytree(OLED/name,DEST/'oled_workspace'/name,dirs_exist_ok=True)
    shutil.copy2(OLED/'export_profile.json',DEST/'oled_workspace/export_profile.json')
    for name in ('drafts','requests','integration_history','exports'):
        copy_missing(OLED/name,DEST/'oled_workspace'/name)
    # Only read-only rendering/adapter reference assets, not a compilable Keil project.
    profile=json.loads((OLED/'export_profile.json').read_text(encoding='utf-8'))
    files=set(profile['sha256'])|{'Hardware/font.h','Hardware/zh12.h','Hardware/ui_text.h'}
    baseline=DEST/'OLEDWorkbench/_internal/firmware_baseline'
    for name in files:
        target=baseline/name;target.parent.mkdir(parents=True,exist_ok=True)
        source=OLED/'firmware_baseline' if (OLED/'firmware_baseline').exists() else WORKSPACE/'defuse_box/firmware'
        shutil.copy2(source/name,target)
    settings={DEST/'OLEDWorkbench/workspace.json':{'workspace':'../oled_workspace','firmware_baseline':'_internal/firmware_baseline'},
        DEST/'WiringWorkbench/data/oled_link.json':{'executable':'../../OLEDWorkbench/OLEDWorkbench.exe','workspace':'../../oled_workspace'}}
    for path,data in settings.items():
        if not path.exists():path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    if (ROOT/'desktop_notices').exists():shutil.copytree(ROOT/'desktop_notices',DEST/'licenses',dirs_exist_ok=True)
    shutil.copy2(ROOT/'docs/SUITE.md',DEST/'使用说明.md')
    receipt={'format':1,'apps':['WiringWorkbench','OLEDWorkbench'],
        'data':['WiringWorkbench/data','oled_workspace/drafts','oled_workspace/requests','oled_workspace/exports'],
        'executables':{name:hashlib.sha256((DEST/name).read_bytes()).hexdigest() for name in ('WorkbenchSuite.exe','WiringWorkbench/WiringWorkbench.exe','OLEDWorkbench/OLEDWorkbench.exe')}}
    (DEST/'suite-manifest.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
    print(DEST/'WorkbenchSuite.exe')

if __name__=='__main__':main()
