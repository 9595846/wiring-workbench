let selectedRequest=null,requestPreviewSeq=0;
const requestLabels={pending:'待处理',reviewing:'处理中',proposed:'待确认',applied:'已应用',cancelled:'已取消'};
function requestName(){if(!loaded||snap()!==saved)throw Error('请先保存当前项目，再提交或应用请求');return loaded;}
function changeLines(a,b,prefix=''){const out=[];for(const key of new Set([...Object.keys(a||{}),...Object.keys(b||{})])){const path=prefix?prefix+'.'+key:key,x=a?.[key],y=b?.[key];if(JSON.stringify(x)===JSON.stringify(y))continue;if(x&&y&&typeof x==='object'&&typeof y==='object')out.push(...changeLines(x,y,path));else out.push(path+': '+JSON.stringify(x)+' → '+JSON.stringify(y));}return out;}
async function refreshRequestList(){const name=loaded;if(!name){$('requestNotice').textContent='先保存或打开一个项目。';return;}
 const rows=await api('/api/requests?name='+encodeURIComponent(name));if(name!==loaded)return;
 $('requestList').replaceChildren();for(const r of rows){const b=document.createElement('button');b.style.cssText='display:block;width:100%;text-align:left;margin:8px 0;white-space:normal';b.textContent=`${requestLabels[r.status]} · ${r.text.slice(0,70)} · ${new Date(r.created_at).toLocaleString()}`;b.onclick=guard(()=>openRequest(r.id));$('requestList').append(b);}
 $('requestNotice').textContent=rows.length?`${rows.length} 条请求；点击查看，提案需确认后应用。`:'暂无请求。提交后请在 Codex 中通知 AI 处理。';
}
async function openRequest(id){const r=await api('/api/request?id='+id);if(r.project!==loaded)throw Error('请先打开请求对应项目');selectedRequest=r;$('requestDetail').hidden=false;$('requestHeading').textContent=requestLabels[r.status]+' · '+r.text;$('requestSummary').textContent=r.summary||'等待你在 Codex 对话中通知 AI 处理。';$('requestDiff').textContent=r.proposal?changeLines(r.base,r.proposal).join('\n')||'无设计变更':'尚无提案';$('applyRequest').disabled=r.status!=='proposed';$('cancelRequest').disabled=['applied','cancelled'].includes(r.status);
 const count=Math.max(r.base.pages.length,r.proposal?.pages.length||0);options($('requestPreviewPage'),Array.from({length:count},(_,i)=>[i,'第 '+(i+1)+' 页']),0);await previewRequest();}
async function previewRequest(){const r=selectedRequest;if(!r)return;const seq=++requestPreviewSeq,pageIndex=Number($('requestPreviewPage').value),notes=[];
 for(const [key,id]of [['base','requestBefore'],['proposal','requestAfter']]){const d=r[key];if(!d||!d.pages[pageIndex]){$(id).hidden=true;continue;}const v=clone(d);v.page=pageIndex;const res=await api('/api/render',{draft:v});if(seq!==requestPreviewSeq||r!==selectedRequest)return;$(id).hidden=false;$(id).src='data:image/png;base64,'+res.png;notes.push(...res.issues.map(i=>i.message));}
 $('requestChecks').textContent=[...new Set(notes)].join('；')||'当前页预览无缺字或越界；硬件功能仍需单独接入。';}
$('requestPreviewPage').onchange=guard(previewRequest);
$('submitRequest').onclick=guard(async()=>{const name=requestName(),text=$('requestText').value;const r=await api('/api/request/create',{name,text,expected_revision:project.revision});$('requestText').value='';await refreshRequestList();await openRequest(r.id);message('请求已保存。请在 Codex 对话中说：处理工作台里的请求。');});
$('refreshRequests').onclick=guard(refreshRequestList);
$('applyRequest').onclick=guard(async()=>{const name=requestName(),r=selectedRequest;if(!r||r.project!==name)throw Error('请求与当前项目不符');if(!confirm('确认将提案应用到已保存草稿？不会修改 Keil 工程。'))return;const before=clone(project),beforeText=snap();$('applyRequest').disabled=true;try{const next=await api('/api/request/apply',{id:r.id});if(loaded===name&&snap()===beforeText){accept(next,name);history=[JSON.stringify(before)];state();}else message('已保存提案，但你当前又进行了编辑，请重新打开项目查看。');await refreshRequestList();await openRequest(r.id);}finally{$('applyRequest').disabled=selectedRequest?.status!=='proposed';}});
$('cancelRequest').onclick=guard(async()=>{if(!selectedRequest)return;await api('/api/request/cancel',{id:selectedRequest.id});await refreshRequestList();await openRequest(selectedRequest.id);});
// Refresh explicitly: never replace an open design or discard unsaved edits in the background.
