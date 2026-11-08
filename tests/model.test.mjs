import assert from 'node:assert/strict';
import {moduleType,instance,connect,endpoint,nets,splitWire,removePin,initial,library} from '../web/model.mjs';
const lib=library(),d=initial(lib);assert.equal(d.wires.length,4);const wire=d.wires[0],p=endpoint(d,wire.a);d.modules[0].x+=50;assert.equal(endpoint(d,wire.a).x,p.x+50);
assert.throws(()=>connect(d,wire.a,wire.a));assert.throws(()=>connect(d,wire.a,wire.b));
const n=splitWire(d,wire.id,{x:350,y:150});assert.equal(d.wires.length,5);assert.equal(nets(d).filter(x=>x.length>1).length,4);
const a={id:'n1',kind:'net',name:'GND',x:0,y:0},b={id:'n2',kind:'net',name:'GND',x:0,y:100};d.nodes.push(a,b);assert(nets(d).some(g=>g.includes('n:n1')&&g.includes('n:n2')));
const m=d.modules[0],pin=m.pins.find(p=>p.name==='3.3V');removePin(d,m.id,pin.id);assert(d.wires.every(w=>![w.a,w.b].some(e=>e.module===m.id&&e.pin===pin.id)));
const cross={modules:[],nodes:[{id:'a',x:0,y:10},{id:'b',x:20,y:10},{id:'c',x:10,y:0},{id:'d',x:10,y:20}],wires:[]};connect(cross,{node:'a'},{node:'b'});connect(cross,{node:'c'},{node:'d'});assert.equal(nets(cross).length,2);
console.log('PASS moving endpoints; duplicate/self rejection; branch topology; named nets; pin deletion; crossings remain disconnected');
