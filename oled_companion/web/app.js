const $ = id => document.getElementById(id);
const names = ['按键与旋钮','光敏检测','姿态检测','舵机测试'];
const dynamicKinds = ['keys','light','imu_xy','imu_z','imu_count','servo_value'];
let draft, selected=0, lastImage, requestId=0, dirty=false, undo=[], redo=[], checkpoint='', saved='', loadedName='default', renderedElements=[], timer=null, servoDeadline=0, busy=false;
const headers={'Content-Type':'application/json','X-OLED-Token':window.OLED_TOKEN};
const snapshot=()=>JSON.stringify(draft);
async function api(url,data){const r=await fetch(url,{method:data?'POST':'GET',headers,body:data?JSON.stringify(data):undefined});const j=await r.json();if(!r.ok)throw Error(j.error||'请求失败');return j;}
function banner(msg,bad=false){$('banner').textContent=msg;$('banner').classList.toggle('error',bad);}
function current(){return draft.pages[draft.page][selected];}
function state(){dirty=snapshot()!==saved;$('revision').textContent=`${loadedName} · 版本 ${draft.revision} · ${dirty?'未保存':'已读取 / 保存'}`;$('saveState').textContent=dirty?'有未保存修改':'草稿已同步';$('saveState').classList.toggle('unsaved',dirty);$('undo').disabled=!undo.length;$('redo').disabled=!redo.length;}
function mark(){const next=snapshot();if(next!==checkpoint){undo.push(checkpoint);if(undo.length>100)undo.shift();redo=[];checkpoint=next;}state();}
function altKey(e=current()){const s=draft.simulation;return e.kind==='light_hint'&&!s.light_ok?'light_bad':e.kind==='imu_status'&&!s.imu_ok?'imu_bad':e.kind==='servo_status'&&s.servo_on?'servo_on':null;}
function editText(e=current()){return altKey(e)?draft.alternatives[altKey(e)]:e.text;}
function changePage(i){if(i===draft.page)return;draft.simulation.servo_on=false;servoDeadline=0;draft.page=i;selected=0;edit();}
function layout(){
 $('pages').replaceChildren();names.forEach((name,i)=>{const b=document.createElement('button');b.textContent=name;b.className=i===draft.page?'active':'';b.setAttribute('aria-current',i===draft.page?'page':'false');b.onclick=()=>changePage(i);$('pages').appendChild(b);});
 $('pageTitle').textContent=names[draft.page];const es=draft.pages[draft.page];selected=Math.max(0,Math.min(selected,es.length-1));
 $('element').replaceChildren();es.forEach((e,i)=>{const o=document.createElement('option');o.value=i;o.textContent=editText(e)||({keys:'按键与旋钮数值',light:'光敏数值',imu_xy:'AX / AY 数值',imu_z:'AZ 与 ID',imu_count:'采样与错误',servo_value:'舵机脉宽'}[e.kind]||e.id);$('element').appendChild(o);});$('element').value=selected;
 const e=current();$('text').value=editText();$('text').disabled=dynamicKinds.includes(e.kind);$('dynamicHint').textContent=$('text').disabled?'此项为动态数值，请使用模拟操作或传感器参数调整。':altKey()?'正在编辑当前模拟状态的提示；其他状态的文字单独保留。':'中文采用现有 12 像素字库；新字会提示缺字。';
 $('x').value=e.x;$('y').value=e.y;$('counter').textContent=`${selected+1} / ${es.length}`;$('ideas').value=draft.ideas;
 for(const k of ['raw','avg','ax','ay','az','id'])$(k).value=draft.simulation[k];for(const k of ['light_ok','imu_ok'])$(k).checked=draft.simulation[k];
 $('simInfo').textContent=`旋钮 ${draft.simulation.enc} 格 · 脉宽 ${draft.simulation.pulse} μs`;
 document.querySelectorAll('[data-key]').forEach(b=>{const k=Number(b.dataset.key);b.querySelector('small').textContent=k===4?'切换下一页':draft.page===3?['','启停舵机','停止舵机','提示音'][k]:'记录按键';});
 state();selection();
}
function displayElement(i){return renderedElements[i]||draft.pages[draft.page][i];}
function bounds(i){const e=draft.pages[draft.page][i],text=displayElement(i).display_text??editText(e);return {x:e.x,y:e.y,w:Math.max(6,[...text].reduce((n,c)=>n+(c.codePointAt(0)<128?6:12),0)),h:[...text].some(c=>c.codePointAt(0)>=128)?12:8};}
function selection(){if(!draft)return;const b=bounds(selected),el=$('selection'),canvas=$('screen');el.style.left=b.x/128*canvas.clientWidth+'px';el.style.top=b.y/64*canvas.clientHeight+'px';el.style.width=b.w/128*canvas.clientWidth+'px';el.style.height=b.h/64*canvas.clientHeight+'px';el.style.display=$('showSelection').checked?'block':'none';$('positionInfo').textContent=`X ${b.x} · Y ${b.y} · ${b.w} × ${b.h} px`;}
async function render(){
 const seq=++requestId;lastImage=null;$('export').disabled=true;
 try{const res=await api('/api/render',{draft});if(seq!==requestId)return;renderedElements=res.elements||[];const img=new Image();img.onload=()=>{if(seq!==requestId)return;const ctx=$('screen').getContext('2d');ctx.clearRect(0,0,128,64);ctx.drawImage(img,0,0);lastImage=res.png;$('export').disabled=false;selection();};img.src='data:image/png;base64,'+res.png;
 $('warnings').replaceChildren();if(res.source_changed){const p=document.createElement('p');p.textContent='工程源文件已变化，需重新核对页面模型。';$('warnings').appendChild(p);}const seen=new Set();for(const issue of res.issues){const key=issue.id+issue.message;if(seen.has(key))continue;seen.add(key);const b=document.createElement('button');b.className='issue';b.textContent=issue.message;b.onclick=()=>{selected=draft.pages[draft.page].findIndex(e=>e.id===issue.id);layout();$('text').focus();};$('warnings').appendChild(b);}if(!res.issues.length&&!res.source_changed)$('warnings').textContent='检查通过 · 当前页面没有缺字或越界';$('warnings').classList.toggle('bad',res.issues.length>0||res.source_changed);
 }catch(e){banner('预览失败：'+e.message,true);}
}
function scheduleRender(){clearTimeout(timer);++requestId;lastImage=null;$('export').disabled=true;timer=setTimeout(render,90);}
function edit(){mark();layout();render();}
function move(x,y){current().x=Math.max(-256,Math.min(256,current().x+x));current().y=Math.max(-256,Math.min(256,current().y+y));edit();}
function history(back){const from=back?undo:redo,to=back?redo:undo;if(!from.length)return;to.push(snapshot());const revision=draft.revision;draft=JSON.parse(from.pop());draft.revision=revision;checkpoint=snapshot();servoDeadline=draft.simulation.servo_on?Date.now()+15000:0;renderedElements=[];layout();render();}
$('undo').onclick=()=>history(true);$('redo').onclick=()=>history(false);
$('element').onchange=e=>{selected=Number(e.target.value);layout();};
$('text').oninput=e=>{const key=altKey();if(key)draft.alternatives[key]=e.target.value;else current().text=e.target.value;mark();scheduleRender();};
for(const k of ['x','y'])$(k).oninput=e=>{const v=Number(e.target.value);if(Number.isInteger(v)&&v>=-256&&v<=256){current()[k]=v;mark();selection();scheduleRender();}};
$('ideas').oninput=e=>{draft.ideas=e.target.value;mark();};
for(const k of ['raw','avg','ax','ay','az','id'])$(k).onchange=e=>{draft.simulation[k]=Math.max(Number(e.target.min),Math.min(Number(e.target.max),Math.trunc(Number(e.target.value))||0));edit();};
for(const k of ['light_ok','imu_ok'])$(k).onchange=e=>{draft.simulation[k]=e.target.checked;edit();};
for(const b of document.querySelectorAll('[data-move]'))b.onclick=()=>move(...b.dataset.move.split(',').map(Number));
for(const b of document.querySelectorAll('[data-key]'))b.onclick=()=>{const k=Number(b.dataset.key),s=draft.simulation;s.key=k;if(k===4){s.servo_on=false;servoDeadline=0;draft.page=(draft.page+1)%4;selected=0;}else if(draft.page===3){if(k===1){s.servo_on=!s.servo_on;if(s.servo_on){s.pulse=1500;servoDeadline=Date.now()+15000;}}else if(k===2)s.servo_on=false;else if(k===3)banner('已模拟提示音事件，未连接真实蜂鸣器。');}edit();};
function turn(delta){const s=draft.simulation;s.enc=Math.max(-9999,Math.min(9999,s.enc+delta));if(draft.page===3&&s.servo_on){s.pulse=Math.max(1400,Math.min(1600,s.pulse+delta*10));servoDeadline=Date.now()+15000;}edit();}
$('left').onclick=()=>turn(-1);$('right').onclick=()=>turn(1);
setInterval(()=>{if(!draft)return;const s=draft.simulation;if(s.servo_on){if(!servoDeadline)servoDeadline=Date.now()+15000;const left=Math.max(0,Math.ceil((servoDeadline-Date.now())/1000));$('servoTimer').textContent=`模拟舵机已开启 · ${left} 秒后自动停止`;if(!left){s.servo_on=false;edit();banner('模拟舵机闲置 15 秒，已自动停止。');}}else $('servoTimer').textContent='模拟舵机已停止 · 切换页面也会停止';},250);
async function save(){if(busy||!draft)return;busy=true;$('save').disabled=true;const sent=structuredClone(draft),name=$('name').value;try{const result=await api('/api/save',{name,draft:sent,expected_revision:name===loadedName?draft.revision:0});loadedName=name;draft.revision=result.revision;saved=JSON.stringify(result);checkpoint=snapshot();state();banner(dirty?'快照已保存，保存期间的新修改仍待保存。':'草稿已保存，可供 MCP 读取。');}catch(e){banner(e.message+' 当前编辑内容仍保留；可更换草稿名另存，或打开草稿重新读取。',true);}finally{busy=false;$('save').disabled=false;}}
$('save').onclick=save;
$('load').onclick=async()=>{if(busy)return;if(dirty&&!confirm('当前有未保存修改，重新打开会丢弃这些修改。继续吗？'))return;busy=true;try{const name=$('name').value;draft=await api('/api/draft?name='+encodeURIComponent(name));loadedName=name;selected=0;undo=[];redo=[];saved=checkpoint=snapshot();servoDeadline=draft.simulation.servo_on?Date.now()+15000:0;renderedElements=[];layout();render();banner(draft.revision?'草稿已读取。':'该名称暂无已保存草稿，已载入原始页面。');}catch(e){banner(e.message,true);}finally{busy=false;}};
$('reset').onclick=async()=>{if(!confirm('恢复当前页面的原始文字和位置？其他页面与便签会保留，可撤销。'))return;try{const page=draft.page,base=await api('/api/default');draft.pages[page]=base.pages[page];const key={1:'light_bad',2:'imu_bad',3:'servo_on'}[page];if(key)draft.alternatives[key]=base.alternatives[key];selected=0;edit();banner('已恢复当前页面，可撤销；保存后才写入草稿。');}catch(e){banner(e.message,true);}};
$('export').onclick=()=>{if(!lastImage)return;const a=document.createElement('a');a.href='data:image/png;base64,'+lastImage;a.download=`oled-page-${draft.page+1}.png`;a.click();};
$('showSelection').onchange=selection;$('help').onclick=()=>$('dialog').showModal();$('close').onclick=()=>$('dialog').close();
let drag=null;
$('screen').onpointerdown=e=>{const r=e.target.getBoundingClientRect(),x=(e.clientX-r.left)*128/r.width,y=(e.clientY-r.top)*64/r.height;for(let i=draft.pages[draft.page].length-1;i>=0;i--){const b=bounds(i);if(x>=b.x&&x<b.x+b.w&&y>=b.y&&y<b.y+b.h){selected=i;layout();drag={x,y,ox:b.x,oy:b.y};e.target.setPointerCapture(e.pointerId);e.target.focus();break;}}};
$('screen').onpointermove=e=>{if(!drag)return;const r=e.target.getBoundingClientRect();current().x=Math.max(-256,Math.min(256,Math.round(drag.ox+(e.clientX-r.left)*128/r.width-drag.x)));current().y=Math.max(-256,Math.min(256,Math.round(drag.oy+(e.clientY-r.top)*64/r.height-drag.y)));$('x').value=current().x;$('y').value=current().y;state();selection();scheduleRender();};
function endDrag(){if(drag){drag=null;mark();render();}}$('screen').onpointerup=endDrag;$('screen').onpointercancel=endDrag;$('screen').onlostpointercapture=endDrag;
window.addEventListener('keydown',e=>{if(!draft)return;const input=/INPUT|TEXTAREA|SELECT/.test(e.target.tagName);if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='s'){e.preventDefault();save();}else if(!input&&(e.ctrlKey||e.metaKey)&&['z','y'].includes(e.key.toLowerCase())){e.preventDefault();history(e.key.toLowerCase()==='z'&&!e.shiftKey);}else if(e.target===$('screen')&&e.key.startsWith('Arrow')){e.preventDefault();const delta={ArrowLeft:[-1,0],ArrowRight:[1,0],ArrowUp:[0,-1],ArrowDown:[0,1]}[e.key];if(delta)move(...delta.map(v=>v*(e.shiftKey?8:1)));}});
window.addEventListener('resize',selection);window.addEventListener('beforeunload',e=>{if(dirty){e.preventDefault();e.returnValue='';}});
(async()=>{try{draft=await api('/api/draft?name=default');saved=checkpoint=snapshot();layout();render();}catch(e){banner('载入失败：'+e.message,true);}})();
