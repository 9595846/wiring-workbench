import asyncio,json,re,sys,subprocess,urllib.request
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import mcp_server,project_store as store
from mcp import ClientSession,StdioServerParameters
from mcp.client.stdio import stdio_client
ROOT=Path(__file__).resolve().parents[1]
def unpack(r):
 assert not r.isError,r
 if r.structuredContent is not None:
  value=r.structuredContent
  return value['result'] if isinstance(value,dict) and set(value)=={'result'} else value
 values=[json.loads(x.text) for x in r.content if x.type=='text']
 return values[0] if len(values)==1 else values
def unpack_list(r):
 value=unpack(r)
 # MCP may emit one JSON content block per list item; a single-item list
 # therefore needs explicit normalization in list-returning tool assertions.
 return [value] if isinstance(value,dict) else value
async def main():
 ident=None;preview=None
 http=subprocess.Popen([sys.executable,'-X','utf8',str(ROOT/'server.py'),'--no-browser'],stdout=subprocess.PIPE,text=True,encoding='utf-8')
 try:
  url=http.stdout.readline().strip();html=urllib.request.urlopen(url).read().decode('utf-8');token=re.search(r'window.WIRING_TOKEN="([^"]+)"',html)[1]
  def web(path,body=None):return json.load(urllib.request.urlopen(urllib.request.Request(url.rstrip('/')+path,data=json.dumps(body).encode() if body else None,headers={'Content-Type':'application/json','X-Wiring-Token':token})))
  async with stdio_client(StdioServerParameters(command=sys.executable,args=['-X','utf8',str(ROOT/'mcp_server.py')])) as (read,write):
   async with ClientSession(read,write) as session:
    await session.initialize();names={x.name for x in (await session.list_tools()).tools};assert len(names)==12,names
    created=unpack(await session.call_tool('create_project',{'title':'MCP 临时验收'}));ident=created['project_id'];assert created['revision']==1
    r=unpack(await session.call_tool('edit_project',{'project_id':ident,'expected_revision':1,'operations':[{'type':'add_custom_module','name':'MCP 模块','pins':['IN','GND'],'x':100,'y':100}]}));assert r['revision']==2
    m=r['operations'][0]['module'];pin=r['operations'][0]['pins'][0]['id']
    r=unpack(await session.call_tool('edit_project',{'project_id':ident,'expected_revision':2,'operations':[{'type':'add_net','name':'GND','x':50,'y':100,'attach':{'module':m,'pin':pin}}]}));assert r['revision']==3
    same=web('/api/project?id='+ident);assert same['revision']==3 and len(same['package']['doc']['wires'])==1
    cp=unpack(await session.call_tool('create_restore_point',{'project_id':ident,'expected_revision':3,'label':'验收恢复点'}));assert cp['revision']==3
    check=unpack(await session.call_tool('check_project',{'project_id':ident}));assert check['count']['info']>0
    pv=unpack(await session.call_tool('preview_project',{'project_id':ident}));preview=Path(pv['path']);assert '<svg' in preview.read_text(encoding='utf-8')
    same['package']['doc']['title']='网页改名';web('/api/project',{'id':ident,'package':same['package'],'expected_revision':3})
    stale=await session.call_tool('edit_project',{'project_id':ident,'expected_revision':3,'operations':[{'type':'rename_project','title':'不应覆盖'}]});assert stale.isError
    restored=unpack(await session.call_tool('restore_project',{'project_id':ident,'checkpoint_id':cp['id'],'expected_revision':4}));assert restored['revision']==5 and restored['package']['doc']['title']=='MCP 临时验收'
    assert web('/api/project?id='+ident)['revision']==5
    points=unpack_list(await session.call_tool('list_restore_points',{'project_id':ident}));assert len(points)>=4
    package=restored['package'];package['doc']['title']='完整更新';updated=unpack(await session.call_tool('update_project',{'project_id':ident,'expected_revision':5,'package':package}));assert updated['revision']==6
    assert unpack(await session.call_tool('read_project',{'project_id':ident}))['revision']==6
    assert any(p['id']==ident for p in unpack_list(await session.call_tool('list_projects',{})))
    assert 'modules'in unpack(await session.call_tool('read_global_library',{}))
    assert 'operations'in unpack(await session.call_tool('get_edit_help',{}))
    print('PASS 12 real MCP tools, SVG/checks, shared HTTP writes, stale rejection, checkpoints and monotonic restore')
 finally:
  http.terminate();http.wait(timeout=10)
  if ident:
   p=store.path_for(ident);assert p.parent.resolve()==store.DATA.resolve();p.unlink(missing_ok=True)
   h=store.history_dir(ident);assert h.resolve().is_relative_to(store.DATA.resolve())
   for f in h.glob('*.json'):f.unlink()
   h.rmdir()
  if preview:
   assert preview.resolve().parent==(ROOT/'mcp_previews').resolve();preview.unlink(missing_ok=True)
asyncio.run(main())
