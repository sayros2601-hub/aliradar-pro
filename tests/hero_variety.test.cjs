const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const script = fs.readFileSync(require('node:path').join(__dirname, '../assets/hero_variety.js'), 'utf8');
const memory = () => { const values=new Map(); return {getItem:k=>values.get(k)||null,setItem:(k,v)=>values.set(k,v),removeItem:k=>values.delete(k)}; };
const blocked = {getItem(){throw Error('blocked')}, setItem(){throw Error('blocked')}};
const catalog = Array.from({length:12},(_,i)=>({id:`p${i}`,key:`photo${i}`,title:`Product ${i}`,href:`/deals/p${i}`,image:`/assets/p${i}.webp`}));
function visit({products=catalog,local=memory(),session=memory()}={}) {
  const events={};
  const photo={addEventListener:(name,fn)=>events[name]=fn};
  const title={};
  const link={dataset:{},querySelector:s=>s==='img'?photo:title};
  const document={querySelector:()=>link,getElementById:()=>({textContent:JSON.stringify(products)})};
  vm.runInNewContext(script,{document,window:{localStorage:local,sessionStorage:session,addEventListener:(name,fn)=>events[name]=fn},Math,Set});
  const p=products.find(p=>p.id===link.dataset.heroId);
  assert.equal(photo.src,p.image); assert.equal(photo.alt,p.title);
  assert.equal(title.textContent,p.title); assert.equal(link.href,p.href);
  return {id:p.id,events,link,photo};
}
for(let run=0;run<50;run++) {
  const local=memory(); let last;
  for(let cycle=0;cycle<3;cycle++) {
    const seen=new Set();
    for(let i=0;i<12;i++) {
      const {id}=visit({local});
      assert.notEqual(id,last,'no adjacent repeats, including cycle boundary');
      assert(!seen.has(id),'no repeats within a full cycle');seen.add(id);last=id;
    }
    assert.equal(seen.size,12);
  }
}
const session=memory();
assert.notEqual(visit({local:blocked,session}).id,visit({local:blocked,session}).id);
visit({local:blocked,session:blocked});
const corrupt=memory();corrupt.setItem('dv_hero_history_v1','{');visit({local:corrupt});
corrupt.setItem('dv_hero_history_v1',JSON.stringify({seen:['removed',null],last:'removed'}));visit({local:corrupt});
const one=[catalog[0]];visit({products:one});
const fail=visit();const failures=new Set([fail.id]);
for(let i=1;i<12;i++) { fail.events.error();assert(!failures.has(fail.link.dataset.heroId));failures.add(fail.link.dataset.heroId); }
fail.events.error(); assert.equal(failures.size,12,'image retry is bounded');
const multilingual=memory();
const en=visit({local:multilingual});
const he=visit({local:multilingual,products:catalog.map(p=>({...p,title:'עברית '+p.id,href:'/he'+p.href}))});
assert.notEqual(en.id,he.id);
en.events.pageshow({persisted:true});
assert.notEqual(en.link.dataset.heroId,he.id);
assert.notEqual(en.link.dataset.heroId,en.id);
console.log('PASS: 1,800 visits, cycle boundaries, storage failure/corruption, locale change, atomic product mapping, one item, bounded image failures');
