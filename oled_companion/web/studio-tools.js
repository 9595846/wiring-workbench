/* Optional workbench controls; existing model and event handlers remain authoritative. */
let lastExportName='',lastExportDirectory='';
const originalApi=api;
api=async function(path,data){const result=await originalApi(path,data);if(path==='/api/studio/export'){lastExportName=result.name;lastExportDirectory=result.directory;toolsState();}return result;};
function toolsState(){
 if(!project)return;
 const active=!!sim,e=element();
 $('modeBadge').textContent=active?'模拟运行 · 不连接硬件':'编辑模式 · 选中后修改';$('modeBadge').dataset.sim=String(active);
 $('editMode').setAttribute('aria-pressed',String(!active));$('simulateMode').setAttribute('aria-pressed',String(active));
 $('saveBadge').textContent=$('revision').textContent;
 $('selectionInfo').textContent=e?`${e.kind==='text'?'文字':e.kind==='image'?'图片':'弹窗'} · X ${e.x} / Y ${e.y} · ${bounds(e).w} × ${bounds(e).h} 像素`:'点击画布元素或从列表选择';
 for(const id of ['alignLeft','alignCenter','alignMiddle','duplicateElement','layerUp','layerDown'])$(id).disabled=active||!e;
 $('openExportFolder').disabled=!lastExportName;$('copyExportPath').disabled=!lastExportDirectory;
}
const previousFrame=frame;frame=function(){previousFrame();toolsState();};
const previousState=state;state=function(){previousState();toolsState();};
const previousRender=render;render=async function(){toolsState();return previousRender();};
$('editMode').onclick=()=>{runGeneration++;sim=null;layout();render();};
$('simulateMode').onclick=()=>{runGeneration++;sim=clone(project);sim.active_dialog=null;render();};
$('toggleGrid').onclick=()=>{const enabled=$('canvasWrap').classList.toggle('grid-on');$('toggleGrid').setAttribute('aria-pressed',String(enabled));$('toggleGrid').textContent=enabled?'隐藏网格':'显示网格';};
function editSelected(fn){if(sim){message('请先切换到编辑布局',true);return;}if(!element())return;fn(element());commit();layout();}
$('alignLeft').onclick=()=>editSelected(e=>e.x=0);
$('alignCenter').onclick=()=>editSelected(e=>e.x=Math.round((128-bounds(e).w)/2));
$('alignMiddle').onclick=()=>editSelected(e=>e.y=Math.round((64-bounds(e).h)/2));
$('duplicateElement').onclick=guard(()=>editSelected(e=>{if(page().elements.length>=32)throw Error('每页最多 32 元素');const c=clone(e);c.id=crypto.randomUUID();c.x=Math.min(256,c.x+4);c.y=Math.min(256,c.y+4);page().elements.push(c);selected=page().elements.length-1;}));
function moveLayer(delta){editSelected(()=>{const next=selected+delta;if(next<0||next>=page().elements.length)return;const es=page().elements;[es[selected],es[next]]=[es[next],es[selected]];selected=next;});}
$('layerUp').onclick=()=>moveLayer(1);$('layerDown').onclick=()=>moveLayer(-1);
$('copyExportPath').onclick=guard(async()=>{await navigator.clipboard.writeText(lastExportDirectory);message('导出目录已复制');});
$('openExportFolder').onclick=guard(async()=>{await api('/api/export/open-folder',{name:lastExportName});message('已请求打开导出文件夹');});
$('addTemplate').onclick=guard(()=>{
 if(project.pages.length>=32)throw Error('最多 32 页');
 const kind=$('templateType').value,key='value_'+crypto.randomUUID().slice(0,8);
 if(Object.keys(project.variables).length>=32)throw Error('最多 32 个变量');
 const title={number:'数值设置',confirm:'确认操作',monitor:'数值监视'}[kind];
 const text=(id,value,y)=>({id,kind:'text',x:0,y,w:128,h:64,text:value});
 const p={name:title,elements:[text('title',title,0),text('value','数值 {'+key+'}',20)],bindings:{}};
 if(kind!=='monitor'){
  p.elements.push(text('hint','按键1打开设置',48));
  p.elements.push({id:'dialog',kind:'dialog',x:8,y:8,w:112,h:48,text:title,mode:kind,variable:key,minimum:0,maximum:100,step:1,confirm:{type:'close'},cancel:{type:'close'}});
  p.bindings.KEY1={type:'open',target:'dialog'};
 }else p.elements.push(text('hint','模拟值 未连接硬件',48));
 project.variables[key]=0;project.pages.push(p);project.page=project.pages.length-1;project.active_dialog=null;selected=0;commit();layout();message('已添加独立模板页；硬件功能仍需单独接入');
});
toolsState();
