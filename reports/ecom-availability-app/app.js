const D=window.JIVO_AVAILABILITY_DATA;
const $=id=>document.getElementById(id);
const title=s=>s.split('-').map(x=>x.charAt(0).toUpperCase()+x.slice(1)).join(' ');
const RUNS=(D.meta&&D.meta.runs)||{};
const SKULEVEL=(D.meta&&D.meta.skuLevel)||{};
let currentRows=[]; let activeSkuSet=null; let activeStrictGroup=null;
function norm(s){return (s||'').toLowerCase().replace(/[^a-z0-9]+/g,' ').trim()}
function scoreSku(s,q){const ns=norm(s), nq=norm(q); if(!nq) return 0; const parts=nq.split(/\s+/).filter(Boolean); let score=0; for(const p of parts){ if(ns.includes(p)) score+=3; else if(p.length>3 && ns.includes(p.slice(0,4))) score+=1; else return -1;} if(ns.includes(nq)) score+=5; return score - Math.min(ns.length/200,2)}
function formatSku(s){return title(s).replace(/\b1l\b/gi,'1L').replace(/\b2l\b/gi,'2L').replace(/\b4l\b/gi,'4L').replace(/\b5l\b/gi,'5L').replace(/\b15l\b/gi,'15L')}
function skuLevelOf(p){return SKULEVEL[p]!==false}
const STRICT_SKU_GROUPS=[
 {id:'extra-light-1l', label:'Jivo Extra Light Olive Oil 1L', terms:['extra light 1l','extra light 1 litre','extra light olive oil 1l','jivo extra light olive oil 1l'], skus:['jivo-extra-light-olive-oil-1l']},
 {id:'canola-1l', label:'Jivo Canola Cold Press Edible Oil 1L', terms:['canola 1l','canola 1 litre','canola oil 1l','jivo canola 1l'], skus:['jivo-cold-pressed-canola-oil-1l']},
 {id:'pomace-1l', label:'Jivo Pomace Olive Oil 1L', terms:['pomace 1l','pomace 1 litre','pomace olive oil 1l','jivo pomace 1l'], skus:['jivo-pomace-olive-oil-1l']}
];
function strictGroupForQuery(q){
 const nq=norm(q); if(!nq) return null;
 const has1l=/(^| )(1l|1 litre|1 liter|1 ltr|1 l)($| )/.test(nq);
 for(const g of STRICT_SKU_GROUPS){ if(g.terms.some(t=>nq===norm(t))) return g; }
 if(has1l && nq.includes('extra') && nq.includes('light')) return STRICT_SKU_GROUPS[0];
 if(has1l && nq.includes('canola')) return STRICT_SKU_GROUPS[1];
 if(has1l && nq.includes('pomace')) return STRICT_SKU_GROUPS[2];
 return null;
}
function strictMatchedSkus(group){const available=new Set(D.skus||[]); return group.skus.filter(s=>available.has(s));}
function init(){
 $('dateTag').textContent='Latest coverage runs · '+D.generatedAt;
 $('metrics').innerHTML=[['Pincodes',D.summary.pincodes],['Platforms',D.summary.platforms],['States',D.summary.states],['SKUs',D.summary.skus]].map(([l,v])=>`<div class="card"><div class="metric mono">${v}</div><div class="label">${l}</div></div>`).join('');
 $('platform').innerHTML=D.platforms.map(p=>`<option value="${p}">${title(p)}</option>`).join('');
 $('state').innerHTML=D.states.map(s=>`<option value="${s}">${s}</option>`).join('');
 $('skuList').innerHTML=D.skus.slice(0,500).map(s=>`<option value="${formatSku(s)}"></option>`).join('');
 const chips=['canola 1l','pomace 1l','extra light 1l','extra virgin','mustard 1l'];
 $('chips').innerHTML=chips.map(c=>`<span class="chip" data-q="${c}">${strictGroupForQuery(c)?'Strict ':''}${c}</span>`).join('');
 document.querySelectorAll('.chip').forEach(c=>c.onclick=()=>{ $('sku').value=c.dataset.q; run(); });
 $('searchBtn').onclick=run; $('platform').onchange=run; $('state').onchange=run; $('sku').addEventListener('keydown',e=>{if(e.key==='Enter')run()}); $('downloadBtn').onclick=downloadCSV;
 if(D.platforms.includes('blinkit')) $('platform').value='blinkit'; if(D.states.includes('Karnataka')) $('state').value='Karnataka';
 run();
}
function matchedSkus(q){
 activeStrictGroup=strictGroupForQuery(q);
 if(!q.trim()) return [];
 if(activeStrictGroup) return strictMatchedSkus(activeStrictGroup);
 return D.skus.map(s=>({s,score:scoreSku(s,q)})).filter(x=>x.score>=0).sort((a,b)=>b.score-a.score).slice(0,30).map(x=>x.s);
}
function run(){
 const platform=$('platform').value, state=$('state').value, q=$('sku').value.trim();
 const sl=skuLevelOf(platform);
 const coverage=D.coverage.find(x=>x.platform===platform && x.state===state); const pins=coverage?coverage.pincodes:[];
 const matches=matchedSkus(q); activeSkuSet=(q&&sl)?new Set(matches):null;
 renderTabs(matches,q,sl);
 const recIndex=new Map();
 for(const r of D.records){ if(r.pl===platform && r.st===state && (!activeSkuSet || activeSkuSet.has(r.s))){ const old=recIndex.get(r.p); if(!old || (r.stock>old.stock) || (r.stock===old.stock && (r.date>old.date))) recIndex.set(r.p,r); }}
 currentRows=pins.map(pin=>{const meta=D.pincodes[pin]||{}; const r=recIndex.get(pin); const cov=r&&r.s==='__coverage__';
   return {pin,city:meta.city||'',state,platform,coverageOnly:!sl,
     available:r?!!r.stock:false, sku:(r&&!cov)?r.s:'', skuCount:cov?r.skuCount:null,
     price:r?r.price:null,mrp:r?r.mrp:null,disc:r?r.disc:null,date:r?r.date:(RUNS[platform]&&RUNS[platform].date)||''};});
 const available=currentRows.filter(r=>r.available).length, seen=currentRows.filter(r=>r.sku||r.coverageOnly).length;
 const rd=RUNS[platform]?` · run ${RUNS[platform].date}`:'';
 if(!sl){
   $('status').innerHTML=`<b>${title(platform)}</b> serves <b>${pins.length}</b> pincodes in ${state}${rd}. <span class="note">Amazon coverage captures serviceability + representative price; per-SKU availability not retained — SKU search shows served pincodes.</span>`;
 } else if(q){
   const strictNote=activeStrictGroup?` <span class="note">Strict 1L mode: counting only the single exact SKU ${activeStrictGroup.label}; all variants, combo, 2L/5L, Extra Virgin and mixed-bundle listings are excluded.</span>`:'';
   $('status').innerHTML=`<b>${title(platform)}</b> in ${state}: <b>${pins.length}</b> served${rd}. SKU matched in ${seen}; <b>available in ${available}</b>; not available/not seen in ${pins.length-available}.${strictNote}`;
 } else {
   $('status').innerHTML=`<b>${title(platform)}</b> serves <b>${pins.length}</b> pincodes in ${state}${rd}. Add a SKU keyword to check availability.`;
 }
 renderTable(q,sl);
}
function renderTabs(matches,q,sl){ const el=$('matchTabs'); if(!q||!sl){el.innerHTML=''; return} if(activeStrictGroup){el.innerHTML=`<span class="tab active">Strict: ${activeStrictGroup.label}</span><span class="tab">${matches.length} exact SKU slug${matches.length===1?'':'s'}</span>`; return} if(!matches.length){el.innerHTML='<span class="tab">No SKU match</span>';return} el.innerHTML=matches.slice(0,8).map((s,i)=>`<span class="tab ${i===0?'active':''}" title="${s}">${formatSku(s).slice(0,42)}</span>`).join('')+ (matches.length>8?`<span class="tab">+${matches.length-8} more</span>`:''); }
function money(v){return v==null||v===''?'—':'₹'+v}
function renderTable(q,sl){ const el=$('table'); if(!currentRows.length){el.innerHTML='<div class="empty">No served pincodes for this platform / state in the latest coverage run.</div>'; return}
 const rows=currentRows.map(r=>{
   let skucell, statuscell;
   if(r.coverageOnly){ skucell=(r.skuCount!=null?r.skuCount+' Jivo SKU'+(r.skuCount===1?'':'s'):'Serviceable')+' · coverage'; statuscell=r.available?'<span class="pill ok">Serving</span>':'<span class="pill neutral">Serves · no Jivo</span>'; }
   else { skucell=r.sku?formatSku(r.sku):(q?'No matching SKU row':'Platform serves pincode'); statuscell=r.available?'<span class="pill ok">Available</span>':(q?'<span class="pill bad">Not available</span>':'<span class="pill neutral">Covered</span>'); }
   return `<div class="row"><div class="mono">${r.pin}</div><div>${r.city}</div><div class="sku">${skucell}</div><div>${statuscell}</div><div>${money(r.price)}</div><div>${money(r.mrp)}</div><div>${r.disc==null?'—':r.disc+'%'}</div><div class="mono">${r.date||'—'}</div></div>`;
 }).join('');
 el.innerHTML='<div class="row head"><div>Pincode</div><div>City</div><div>Matched SKU</div><div>Status</div><div>Price</div><div>MRP</div><div>Discount</div><div>Run date</div></div>'+rows;
}
function downloadCSV(){ if(!currentRows.length)return; const header=['pincode','city','state','platform','status','matched_sku','sku_count','price','mrp','discount_pct','run_date']; const lines=[header.join(',')]; for(const r of currentRows){lines.push([r.pin,r.city,r.state,r.platform,r.coverageOnly?(r.available?'serving':'serves_no_jivo'):(r.available?'available':'not_available'),r.sku,r.skuCount??'',r.price??'',r.mrp??'',r.disc??'',r.date].map(v=>'"'+String(v).replaceAll('"','""')+'"').join(','));} const blob=new Blob([lines.join('\n')],{type:'text/csv'}); const a=document.createElement('a'); a.href=URL.createObjectURL(blob); a.download='jivo_availability_'+$('platform').value+'_'+$('state').value.replace(/\s+/g,'_')+'.csv'; a.click(); URL.revokeObjectURL(a.href); }
init();
