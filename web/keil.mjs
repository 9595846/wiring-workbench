import {nets,key} from './model.mjs';
export function connectedPins(doc,wire){const members=new Set(nets(doc).find(g=>g.includes(key(wire.a)))||[]);return doc.modules.flatMap(m=>m.pins.filter(p=>members.has(key({module:m.id,pin:p.id}))).map(p=>({module:m.id,pin:p.id,name:m.name+' / '+p.name,pinName:p.name})));}
export function compareBindings(doc,scan){
 return doc.wires.map(w=>{const b=w.codeBinding;if(!b)return {wire:w.id,status:'unbound',message:'未指定代码用途/证据，尚未核对',evidence:[]};
 const physical=connectedPins(doc,w).find(p=>p.module===b.controller.module&&p.pin===b.controller.pin);
 if(!physical)return {wire:w.id,status:'unknown',message:'绑定的控制器针脚已不在此连接网络中，请重新选择',evidence:[]};
 if(!scan)return {wire:w.id,status:'unknown',message:'已有绑定，需重新扫描当前工程后核对',evidence:[]};
 if(b.project!==scan.project||b.target!==scan.target)return {wire:w.id,status:'unknown',message:'当前扫描工程或目标与此绑定不同，请重新指定证据',evidence:[]};
 const ev=scan.evidence.filter(e=>e.file===b.file&&e.symbols.includes(b.symbol)),pins=[...new Set(ev.map(e=>e.pin))];
 if(!/^P[A-K](?:[0-9]|1[0-5])$/.test(physical.pinName))return {wire:w.id,status:'unknown',message:'图纸针脚名称不是可识别的 PA0～PK15 格式，请确认控制器针脚',evidence:ev};
 if(!ev.length)return {wire:w.id,status:'unknown',message:'当前扫描未找到绑定证据；可能是宏、动态配置或排除文件',evidence:[]};
 if(pins.length>1)return {wire:w.id,status:'unknown',message:'同一符号解析出多个针脚：'+pins.join('、')+'，需人工确认分支/重配置',evidence:ev};
 return {wire:w.id,status:pins[0]===physical.pinName?'candidate':'difference',message:pins[0]===physical.pinName?'静态候选与图纸相符；仍需确认编译条件和实际运行路径':`待确认差异：图纸 ${physical.pinName}，代码候选 ${pins[0]}（不能据此认定实际运行配置）`,evidence:ev};
 });
}
