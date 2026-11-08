import {clone,endpoint} from './model.mjs';
const fail=s=>{throw Error(s);};
export function validatePackage(input){
 if(input?.format!=='wiring-workbench'||input.version!==1)fail('不支持的项目格式或版本');
 const p=clone(input),d=p.doc;if(!d||d.version!==1||typeof d.title!=='string'||d.title.length>120)fail('图纸信息无效');
 if(d.powerDisplay!==undefined&&!['full','compact'].includes(d.powerDisplay))fail('供电显示模式无效');
 for(const [k,max]of [['modules',60],['wires',200],['nodes',300],['annotations',200]])if(!Array.isArray(d[k])||d[k].length>max)fail('对象数量或格式无效：'+k);
 if(!Array.isArray(p.library)||p.library.length>200)fail('模块库格式无效');
 const str=(v,max=120)=>typeof v==='string'&&v.length<=max;
 const num=v=>Number.isFinite(v)&&Math.abs(v)<=10000;
 const ids=new Set();const id=o=>{if(!str(o.id)||!o.id||ids.has(o.id))fail('对象 ID 无效或重复');ids.add(o.id);};
 function module(m,placed){if(!str(m.name)||!str(m.kind)||!Number.isInteger(m.version)||m.version<1||!Array.isArray(m.pins)||m.pins.length>64)fail('模块格式无效');if(placed&&![m.x,m.y,m.w,m.h].every(num))fail('模块尺寸坐标无效');if(placed&&(m.w<120||m.h<100))fail('模块尺寸过小');const seen=new Set();for(const pin of m.pins){if(!str(pin.id)||seen.has(pin.id)||!str(pin.name)||!['left','right','top','bottom'].includes(pin.side)||!num(pin.offset)||!str(pin.voltage)||!str(pin.role))fail('针脚格式无效');if(pin.electrical!==undefined){const e=pin.electrical;if(!e||!['unknown','gnd','power_out','power_in','input','output','open_drain','passive'].includes(e.type)||typeof e.required!=='boolean'||!['unknown','present','absent'].includes(e.pullup))fail('针脚电气属性无效');}seen.add(pin.id);}}
 for(const m of d.modules){id(m);module(m,true);}for(const m of p.library)module(m,false);
 const libids=new Set();for(const m of p.library){if(!str(m.id)||libids.has(m.id))fail('模块库 ID 重复');libids.add(m.id);}
 for(const n of d.nodes){id(n);if(!['junction','net'].includes(n.kind)||!num(n.x)||!num(n.y)||!str(n.name))fail('连接点无效');}
 for(const a of d.annotations){id(a);if(!['note','title','arrow','group'].includes(a.kind)||![a.x,a.y,a.w,a.h].every(num)||!str(a.text,2000)||!/^#[0-9a-f]{6}$/i.test(a.color))fail('标注无效');}
 for(const w of d.wires){id(w);if(!/^#[0-9a-f]{6}$/i.test(w.color)||!str(w.name)||!str(w.purpose)||!['ortho','straight'].includes(w.style)||!Array.isArray(w.bends)||w.bends.length>100||w.bends.some(p=>!num(p.x)||!num(p.y)))fail('导线格式无效');if(w.routeFixed!==undefined){const f=w.routeFixed;if(!f||!str(f.stamp,64)||!['ortho','straight'].includes(f.style)||!Array.isArray(f.points)||f.points.length>500||f.points.some(p=>!num(p.x)||!num(p.y)))fail('固定线路快照无效');}if(w.locked!==undefined&&typeof w.locked!=='boolean')fail('线路锁定状态无效');if(w.lockedBends!==undefined&&(!Array.isArray(w.lockedBends)||w.lockedBends.length>500||w.lockedBends.some(p=>!num(p.x)||!num(p.y))))fail('锁定线路形状无效');for(const k of ['routeVariant','routePriority'])if(w[k]!==undefined&&(!Number.isInteger(w[k])||Math.abs(w[k])>100000))fail('布线参数无效');if(w.codeBinding!==undefined){const b=w.codeBinding;if(!b||!str(b.file,500)||!str(b.symbol)||!str(b.project,1000)||!str(b.target)||!b.controller||!str(b.controller.module)||!str(b.controller.pin))fail('代码核对绑定格式无效');}for(const ref of [w.a,w.b]){if(!ref||!!ref.node===!!ref.module||!endpoint(d,ref))fail('导线引用不存在的端点');}}
 return p;
}
export function packageProject(doc,library){return validatePackage({format:'wiring-workbench',version:1,doc,library});}
