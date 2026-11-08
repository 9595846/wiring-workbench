import {nets,key} from './model.mjs';
export const pinKinds=[['unknown','未知'],['gnd','地 / 电源负极'],['power_out','电源输出'],['power_in','电源输入'],['input','信号输入'],['output','推挽信号输出'],['open_drain','开漏 / 开集电极'],['passive','无源触点 / 被动端']];
export function voltageRange(text){const s=String(text??'').trim();const m=s.match(/^(\d+(?:\.\d+)?)\s*(?:V|伏)?(?:\s*(?:~|～|至|-)\s*(\d+(?:\.\d+)?)\s*(?:V|伏)?)?$/i);if(!m)return null;const a=Number(m[1]),b=Number(m[2]??m[1]);return a<=b&&b<=1000?[a,b]:null;}
export function electricalCheck(doc){
 const index=new Map();for(const m of doc.modules)for(const pin of m.pins){const ref={module:m.id,pin:pin.id};index.set(key(ref),{m,pin,ref,type:pin.electrical?.type||'unknown',v:voltageRange(pin.voltage)});}
 const issues=[],groups=nets(doc);let checkedNets=0;
 const label=p=>p.m.name+' / '+p.pin.name;
 for(const [i,members]of groups.entries()){
  const pins=members.map(k=>index.get(k)).filter(Boolean),set=new Set(members),wires=doc.wires.filter(w=>set.has(key(w.a))&&set.has(key(w.b))),connected=!!wires.length||members.length>1;
  const add=(severity,code,message,affected=pins)=>issues.push({id:'net'+i+'-'+code,severity,code,message,net:i+1,pins:affected.map(p=>p.ref),wires:wires.map(w=>w.id),nodes:doc.nodes.filter(n=>set.has(key({node:n.id}))).map(n=>n.id)});
  if(!connected){for(const p of pins)if(p.pin.electrical?.required)add('warning','unconnected-'+p.pin.id,'必接针脚未连接：'+label(p),[p]);continue;}
  checkedNets++;
  if(!pins.length){add('info','no-pins','此网络只有连接点或网络标记，尚未接到模块针脚。');continue;}
  const unknown=pins.filter(p=>p.type==='unknown');if(unknown.length)add('info','unknown-type','针脚电气类型待确认：'+unknown.map(label).join('、'),unknown);
  const active=pins.filter(p=>!['unknown','gnd','passive'].includes(p.type)),missingV=active.filter(p=>!p.v);if(missingV.length)add('info','unknown-voltage','电压或范围未知 / 格式无效：'+missingV.map(label).join('、'),missingV);
  const grounds=pins.filter(p=>p.type==='gnd'),sources=pins.filter(p=>p.type==='power_out'),drivers=pins.filter(p=>p.type==='output'),drains=pins.filter(p=>p.type==='open_drain');
  if(grounds.length&&sources.some(p=>!p.v||p.v[1]>0.05))add('error','polarity','电源输出与地/负极处于同一网络，存在短路或极性接错风险。',[...grounds,...sources]);
  if(sources.length>1){const known=sources.filter(p=>p.v),mismatch=known.some((p,i)=>known.slice(i+1).some(q=>p.v[1]<q.v[0]-0.05||q.v[1]<p.v[0]-0.05));add(mismatch?'error':'warning','power-parallel',mismatch?'不同电压的电源输出直接相连。':'多路电源输出并联；需确认电源是否允许并联，不能仅凭电压相同判断兼容。',sources);}
  if(drivers.length>1||drivers.length&&drains.length)add('error','output-contention','多个推挽输出，或推挽与开漏输出处于同一网络，存在输出争用风险。',[...drivers,...drains]);
  if(grounds.length&&drivers.length)add('warning','output-ground','推挽输出直接连接地，需确认是否会产生短路电流。',[...grounds,...drivers]);
  if(sources.length&&[...drivers,...drains].length)add('warning','signal-power','电源输出直接接信号输出，需核对是否误接。',[...sources,...drivers,...drains]);
  const voltageSources=[...sources,...drivers].filter(p=>p.v),sinks=pins.filter(p=>['power_in','input','open_drain'].includes(p.type)&&p.v);
  const bad=[];for(const src of voltageSources)for(const sink of sinks)if(src!==sink&&(src.v[0]<sink.v[0]-0.05||src.v[1]>sink.v[1]+0.05))bad.push(label(src)+' ('+src.pin.voltage+') → '+label(sink)+' ('+sink.pin.voltage+')');
  if(bad.length)add('error','voltage-range','源端电压超出接收端声明范围：'+bad.join('；'));
  const powerInputs=pins.filter(p=>p.type==='power_in');if(powerInputs.length&&!sources.length)add('info','no-power-source','电源输入未连接已声明的电源输出，请检查供电来源。',powerInputs);
  if(drains.length&&!pins.some(p=>p.pin.electrical?.pullup==='present'))add(pins.some(p=>p.pin.electrical?.pullup==='absent')?'warning':'info','pullup','开漏网络未声明已有上拉；请确认实际模块是否带上拉及上拉电压，勿盲目并联。',drains);
 }
 const count={error:0,warning:0,info:0};for(const x of issues)count[x.severity]++;
 return {issues,count,checkedNets,scope:'仅基于已填写属性做静态检查；不验证供电容量、GPIO复用/定时器、限流阻值、真实电平、实物针序或 Keil 配置。',summary:count.error?'检出需处理的接线风险':count.warning?'存在待确认的连接风险':count.info?'已填写规则未检出风险，仍有未知信息':'已填写规则未检出风险；不代表电路已通过实物验证'};
}
