import assert from 'node:assert/strict';
import {library,initial} from '../web/model.mjs';
import {packageProject,validatePackage} from '../web/persistence.mjs';
const lib=library(),doc=initial(lib),before=JSON.stringify(doc.wires);
doc.modules[1].oledLink={name:'project_my_oled',page:0,revision:1};
const pkg=packageProject(doc,lib);
assert.deepEqual(validatePackage(JSON.parse(JSON.stringify(pkg))).doc.modules[1].oledLink,doc.modules[1].oledLink);
assert.equal(JSON.stringify(doc.wires),before);
for(const bad of [{name:'../private',page:0,revision:1},{name:'project_test',page:-1,revision:1},{name:'project_test',page:0,revision:'1'}]){
 const p=structuredClone(pkg);p.doc.modules[1].oledLink=bad;assert.throws(()=>validatePackage(p));
}
console.log('PASS OLED binding roundtrip, invalid metadata rejected, original wiring unchanged');
