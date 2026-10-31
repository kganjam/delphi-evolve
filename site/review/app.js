'use strict';
// Exact signs use reduced BigInt fractions. Floating point is used only to draw SVG.
const Q = (n, d = 1n) => {
  n = BigInt(n); d = BigInt(d);
  if (!d) throw new Error('Zero denominator');
  if (d < 0n) { n = -n; d = -d; }
  let a = n < 0n ? -n : n, b = d;
  while (b) [a, b] = [b, a % b];
  return { n: n / a, d: d / a };
};
const add = (a,b) => Q(a.n*b.d+b.n*a.d,a.d*b.d);
const neg = a => Q(-a.n,a.d);
const sub = (a,b) => add(a,neg(b));
const mul = (a,b) => Q(a.n*b.n,a.d*b.d);
const div = (a,b) => Q(a.n*b.d,a.d*b.n);
const less = (a,b) => a.n*b.d < b.n*a.d;
const fmt = a => a.d === 1n ? String(a.n) : `${a.n}/${a.d}`;
const number = a => Number(a.n)/Number(a.d);
const el = id => document.getElementById(id);
const put = (id,text) => { el(id).textContent = text; };
const svgNS = 'http://www.w3.org/2000/svg';
const draw = (tag, attributes, text = '') => {
  const node = document.createElementNS(svgNS,tag);
  Object.entries(attributes).forEach(([k,v]) => node.setAttribute(k,String(v)));
  node.textContent = text; el('plot').append(node); return node;
};
let activeCase = 'domain';
function clearPlot(title, description) {
  el('plot').replaceChildren();
  draw('title',{id:'plot-accessible-title'},title);
  draw('desc',{id:'plot-accessible-description'},description);
}
function table(headers, rows) {
  el('table-head').replaceChildren(); el('table-body').replaceChildren();
  const head = document.createElement('tr');
  headers.forEach(text => { const th = document.createElement('th'); th.scope='col'; th.textContent=text; head.append(th); });
  el('table-head').append(head);
  rows.forEach(values => {
    const tr = document.createElement('tr');
    values.forEach(text => { const td = document.createElement('td'); td.textContent=text; tr.append(td); });
    el('table-body').append(tr);
  });
}
function renderModes() {
  const ratio = activeCase === 'ratio';
  const J = ratio ? [Q(1),Q(-1),Q(1011,1000),Q(-101,100)] : [Q(1),Q(-2),Q(2),Q(-3)];
  const d = ratio ? Q(11,10) : Q(10);
  const length = ratio ? Q(5) : Q(el('length').value);
  const mult = ratio || el('boundary').value === 'neumann' ? Q(1) : Q(2);
  const [a,b,c,e] = J, trace = add(a,e), determinant = sub(mul(a,e),mul(b,c));
  const B = add(mul(d,a),e), cutoff = div(B,d);
  const detAt = q => add(sub(mul(d,mul(q,q)),mul(B,q)),determinant);
  const modes = [];
  for (let n=1;n<=200;n++) {
    const k = div(mul(mult,Q(n)),length), q = mul(k,k), det = detAt(q);
    modes.push({n,q,det,unstable:det.n<0n});
    if (!less(q,cutoff)) break;
  }
  const unstable = modes.filter(m => m.unstable);
  put('case-kicker',ratio ? 'A universal threshold fails' : 'Continuum ≠ finite domain');
  put('case-title',ratio ? 'A ratio of 1.1 is enough in this model.' : 'Which modes fit?');
  put('case-description',ratio ? 'Our proposed universal threshold of 10 was wrong. A specific declared linear system has a growing admissible mode with Dᵥ/Dᵤ = 11/10.' : 'The continuum instability band stays fixed. Changing the domain or its boundary changes the discrete modes that can enter it.');
  put('model',`J = [[${fmt(a)}, ${fmt(b)}], [${fmt(c)}, ${fmt(e)}]]\nDᵤ = 1; Dᵥ = ${fmt(d)}\ntrace J = ${fmt(trace)}; det J = ${fmt(determinant)}`);
  el('model').style.whiteSpace='pre-line';
  put('plot-title','Admissible squared wavenumbers q');
  const left=55,right=675, y=166, maxQ=ratio ? 0.2 : 1.1;
  const x = q => left+(right-left)*q/maxQ;
  // Band endpoints are for plotting only. Mode classifications above are exact.
  const disc = number(mul(B,B))-4*number(d)*number(determinant);
  const lo=(number(B)-Math.sqrt(disc))/(2*number(d)), hi=(number(B)+Math.sqrt(disc))/(2*number(d));
  clearPlot('Admissible modes and the negative determinant band', `${unstable.length} canonical modes have negative determinant. Only q up to ${maxQ} are drawn; the table includes the finite tail check.`);
  draw('rect',{x:x(lo),y:62,width:x(hi)-x(lo),height:154,fill:'#704c2f',opacity:0.48,rx:5});
  draw('text',{x:(x(lo)+x(hi))/2,y:46,'text-anchor':'middle',fill:'#f3bd79'},'det(J − qD) < 0');
  draw('line',{x1:left,y1:y,x2:right,y2:y,stroke:'#647b83','stroke-width':1});
  [0,maxQ/2,maxQ].forEach(v => { draw('line',{x1:x(v),x2:x(v),y1:y,y2:y+7,stroke:'#647b83'});draw('text',{x:x(v),y:y+31,'text-anchor':'middle'},String(Number(v.toFixed(3)))); });
  modes.filter(m => number(m.q)<=maxQ).forEach((m,i) => {
    const xx=x(number(m.q)), yy=y-(i%2)*38;
    draw('line',{x1:xx,x2:xx,y1:yy,y2:y,stroke:'#637c82'});
    draw('circle',{cx:xx,cy:yy,r:8,fill:m.unstable?'#f3bd79':'#83e0d0'});
    draw('text',{x:xx,y:yy-20,'text-anchor':'middle'},`n=${m.n}`);
  });
  put('plot-note',`Shaded: negative determinant band. Dots: canonical modes. Axis limited to q ≤ ${maxQ}; all remaining modes are covered by the exact tail inequality below.`);
  put('verdict-title',unstable.length ? `${unstable.length} growing linear mode${unstable.length===1?'':'s'} admitted` : 'No growing linear mode admitted');
  put('verdict-detail',unstable.length ? `At n = ${unstable[0].n}, q = ${fmt(unstable[0].q)} and det(J − qD) = ${fmt(unstable[0].det)}. This calculation does not establish a stable nonlinear pattern.` : 'No admissible mode enters the negative-determinant band. This excludes diffusion-driven linear growth under these conditions; it does not exclude every finite-amplitude outcome.');
  el('verdict-title').dataset.modeCount=String(unstable.length);
  table(['n','q','det(J − qD)','Linear classification'],modes.map(m=>[String(m.n),fmt(m.q),fmt(m.det),m.unstable?'growing':'no positive-real-part eigenvalue']));
  put('calculation-note',`Trace is negative for all q ≥ 0. With B = Dᵥa + e, every q ≥ B/Dᵥ = ${fmt(cutoff)} has det(J − qD) ≥ det J > 0. The finite enumeration includes the first such mode. BigInt fractions decide signs; decimal coordinates only place the drawing. Periodic modes are counted canonically, not by sine/cosine multiplicity.`);
  put('receipt-kind','Recorded Lean run');
  put('receipt-title',ratio ? 'A compiled certificate for this fixed counterexample' : 'Compiled examples at L = π and L = 2π, Neumann boundaries');
  put('receipt-description',ratio ? 'The preceding primary compiled the generated classification for this fixed model and independently checked a finite-difference eigenproblem. This page preserves that attribution; it does not invoke Lean.' : 'The earlier release contains executed Lean receipts for the two fixed Neumann examples. Other control settings here are exact browser calculations; this page does not compile a new certificate for them.');
  el('receipt-link').href=ratio ? 'https://github.com/kganjam/delphi-evolve/blob/596ae9eda8a687b22faaf893ca1498aa71207ba9/artifacts/integration/codex-api/service-fixed-review.json' : 'https://github.com/kganjam/delphi-evolve/blob/51a38057aebe7e7e0801d8f67af7fd4a81a8935f/artifacts/turing_scope/lean_receipt.json';
}
function renderVolume() {
  const n=Number(el('mode').value), s=Q(3,2);
  const integral=n%2 ? div(mul(Q(2),s),Q(n)) : Q(0);
  const kr2=mul(div(Q(n),s),div(Q(n),s));
  put('case-kicker','An omitted conservation law'); put('case-title','Pinned ends are not the whole condition.');
  put('case-description','The first sine mode vanishes at both ends, but changes total liquid volume to first order. Our benchmark originally treated it as admissible.');
  put('model','η(z) = sin(nπz/L)\nFixed volume requires ∫η(z) dz = 0.\nL = 3πr/2');
  put('plot-title','Radial perturbation along the bridge');
  clearPlot('Sine perturbation of a fixed-volume liquid bridge',n===1?'The one-half-wave perturbation has positive mean and violates first-order volume conservation.':'The two-half-wave perturbation has zero mean and satisfies the first-order volume constraint.');
  let path='';
  for(let i=0;i<=240;i++){const xx=55+620*i/240, yy=145-76*Math.sin(n*Math.PI*i/240);path+=`${i?'L':'M'}${xx.toFixed(2)},${yy.toFixed(2)} `;}
  draw('path',{d:`${path}L675,145 L55,145 Z`,fill:n===1?'#704c2f':'#315e58',opacity:0.65});
  draw('line',{x1:55,y1:145,x2:675,y2:145,stroke:'#647b83'});
  [55,675].forEach(xx=>draw('line',{x1:xx,y1:48,x2:xx,y2:240,stroke:'#647b83','stroke-width':3}));
  draw('path',{d:path,fill:'none',stroke:n===1?'#f3bd79':'#83e0d0','stroke-width':3});
  draw('text',{x:55,y:265,'text-anchor':'middle'},'z = 0');draw('text',{x:675,y:265,'text-anchor':'middle'},'z = L');
  put('plot-note','The curve is the declared perturbation shape, not a simulated evolving interface. Its signed integral determines first-order volume admissibility.');
  put('verdict-title',integral.n===0n?'Passes the first-order volume test':'Rejected: this mode changes volume');
  put('verdict-detail',integral.n===0n?'The n = 2 mode has zero mean. At this length, (kr)² = 16/9 > 1, so it does not supply the proposed instability witness.':'Here ∫η dz / r = 3, not zero. Even though (kr)² = 4/9 < 1, this mode cannot witness instability of the declared fixed-volume bridge.');
  el('verdict-title').dataset.volumeAdmissible=String(integral.n===0n);
  table(['n','∫η dz / r','(kr)²','Fixed-volume test'],[[String(n),fmt(integral),fmt(kr2),integral.n===0n?'passes to first order':'fails']]);
  put('calculation-note','The exact arithmetic evaluates the analytical integral 2L/(nπ) for odd n and zero for even n. A zero first-order integral alone is not a full nonlinear stability proof.');
  put('receipt-kind','Analytic + source review');put('receipt-title','The omitted constraint was caught before evaluation');
  put('receipt-description','The review derives the volume condition and links the primary liquid-bridge source. This example has not been compiled in Lean. The defective benchmark family was removed.');
  el('receipt-link').href='https://github.com/kganjam/delphi-evolve/blob/19fae04003dead3d357d0eb0d34dace022091b9f/planning/rethink/CODEX-BENCHMARK-SEMANTICS.md';
}
function render() {
  document.querySelectorAll('[data-case]').forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.case===activeCase)));
  el('domain-controls').hidden=activeCase!=='domain';el('volume-controls').hidden=activeCase!=='volume';
  if(activeCase==='volume')renderVolume();else renderModes();
}
document.querySelectorAll('[data-case]').forEach(button=>button.addEventListener('click',()=>{activeCase=button.dataset.case;render();}));
['length','boundary','mode'].forEach(id=>el(id).addEventListener('change',render));
render();
