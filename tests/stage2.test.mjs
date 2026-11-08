import assert from 'node:assert/strict';
import {library,initial,wirePoints} from '../web/model.mjs';
import {packageProject,validatePackage} from '../web/persistence.mjs';
const lib=library(),doc=initial(lib),p=packageProject(doc,lib);assert.deepEqual(validatePackage(JSON.parse(JSON.stringify(p))),p);
const bad=structuredClone(p);bad.doc.wires[0].a.pin='missing';assert.throws(()=>validatePackage(bad));
const bad2=structuredClone(p);bad2.doc.modules[0].x=Infinity;assert.throws(()=>validatePackage(bad2));
assert.throws(()=>validatePackage({...p,version:99}));
for(const w of doc.wires){const ps=wirePoints(doc,w);for(let i=1;i<ps.length;i++)assert(ps[i-1].x===ps[i].x||ps[i-1].y===ps[i].y);}
const lanes=doc.wires.map(w=>wirePoints(doc,w).filter((p,i,ps)=>i&&p.x===ps[i-1].x&&p.y!==ps[i-1].y).map(p=>p.x));assert(new Set(lanes.flat()).size>=3);
doc.modules[1].x=10;doc.modules[1].y=420;for(const w of doc.wires){const ps=wirePoints(doc,w);assert(ps.length>=2);assert(ps.every(p=>Number.isFinite(p.x)&&Number.isFinite(p.y)));}
console.log('PASS JSON roundtrip, format/reference/coordinate rejection, orthogonal routes, staggered lanes, reversed layout');
