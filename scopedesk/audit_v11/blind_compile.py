import json,re,math
from fractions import Fraction as F
exec(open('blind_turing.py').read().split("out={}")[0])   # reuse parse helpers
tur=json.load(open('blind_turing_out.json'))
km=json.load(open('blind_km_out.json')); hmhd=json.load(open('blind_hmhd_out.json'))
gh=json.load(open('blind_gh_out.json')); wl=json.load(open('blind_wl_out.json'))
ids=[json.loads(l) for l in open('blind_input.jsonl')]
text={x['id']:x['request_text'] for x in ids}
V={}
def put(i,v,conf,rule,amb): V[i]=dict(id=i,verdict=v,confidence=conf,rule=rule,ambiguity=amb)
# Turing
def band(J,Dv):
    a,b,c,d=J; det=a*d-b*c; B=Dv*a+d
    disc=B*B-4*Dv*det
    if disc<0: return None
    s=math.sqrt(float(disc)); return ((float(B)-s)/(2*float(Dv)),(float(B)+s)/(2*float(Dv)))
for i,d in tur.items():
    J=[F(v) for v in d['J']]; Dv=F(d['Dv']); bcn=d['bc']; r=d['res']
    bd=band(J,Dv)
    if bcn is None:
        outs={k:r[k]['unst'] for k in r if not (i.startswith('t2') and k=='D')}
        put(i,'underdetermined','high','Boundary type not stated => not known (text rule); admissible-mode outcome depends on BC: '+str(outs)+f'; unstable band q in {bd}',
            'none under the text rule; (if BC were irrelevant it would not matter, but outcomes differ across BCs)')
        continue
    rr=r[bcn]
    amb='none'; conf='high'
    if i=='t2-0011':
        put(i,'out_of_scope','low','det J<0 (and the quoted inequality involves sqrt of a negative): steady state is unstable without diffusion; any unstable mode is kinetic, not diffusion-driven',
            'Admissible unstable modes exist (growth comes from kinetics, not diffusion); if "diffusion-driven" is read as merely "exists growing mode" verdict would be applies. Also the premise "inequality satisfied" is ill-defined for det<0.'); continue
    if i=='ts-0008':
        put(i,'applies','medium','det J=0 exactly; h(q)=q(30q-6.5)<0 for 0<q<0.2167; n=1,2 Dirichlet modes (q=0.04,0.16) are unstable',
            'det J=0 so base state is marginal (zero eigenvalue) in kinetics; strict textbook DDI needs det>0. Growing mode exists only due to diffusion. A strict reading gives out_of_scope.'); continue
    if i=='ts-0018':
        put(i,'out_of_scope','high','det J=0, unstable band 0<q<0.2167 but smallest admissible Neumann q=(2/3)^2=0.444 lies outside',
            'det J=0 marginal state (same caveat as ts-0008) but both readings give out_of_scope'); continue
    if not rr['ineq']:
        put(i,'out_of_scope','high',f'quoted DDI inequality is actually FALSE (D_v f_u + D_u g_v = {Dv*J[0]+J[3]}); no admissible unstable mode on this domain either; unstable band {bd}',
            'requester premise is false; alternative reading "premise false so statement n/a" also out_of_scope'); continue
    v='applies' if rr['unst'] else 'out_of_scope'
    put(i,v,conf,f'bc={bcn}; exact rational test h(q)<0 over admissible modes: unstable mode exists={rr["unst"]}; unstable band q in {bd}',amb)
# KM
for i,(v,rel,kind) in km.items():
    conf='high' if abs(abs(rel)-0.1)>0.02 else 'medium'
    put(i,v,conf,f'exact absorbing-chain fixation prob via Fractions; formula={kind}; rel err={rel:+.4f} vs 10% threshold','none (rel. error measured against exact value; against approx would give same verdict)' )
# HM, HD
for i,v in hmhd.items():
    t=text[i]
    if i.startswith('hm'):
        conf='high'
        amb='none'
        if v=='underdetermined': amb='frequency not stated; sign of exact covariance (-c+rb+d(r+(1-r)p)) flips within p in (0,1)'
        put(i,v,conf,'cov(g,w)=p(1-p)[-c+rb+d(r+(1-r)p)]; compare sign with rb-c',amb)
    else:
        if v=='underdetermined': put(i,v,'high','cost C not stated; V/C cannot be evaluated','none')
        else: put(i,v,'high','V/C must be <=1 (<1 here): mixed ESS with Hawk prob V/C exists iff V<C','none; V==C case would be edge but does not occur')
# GH
for i,(v,m) in gh.items():
    if v=='underdetermined': put(i,v,'high','density not given; H_cr (and any threshold) needs rho','none')
    else:
        tap='tapered' if 'tapers' in text[i] else 'uniform'
        put(i,v,'medium' if tap=='tapered' else 'high',f'{tap}; g=9.81; H/H_unif={m[0]:.3f}, H/H_exact={m[1]:.3f}; exact via ODE (EI th\')\'+W th=0, th\'(0)=0, th(H)=0',
            'g not stated (assumed 9.81; margins 5-20% so insensitive); for tapered columns the text does not say which diameter the uniform formula uses (base diameter assumed, as D in formula is "base diameter")' if tap=='tapered' else 'g not stated (assumed 9.81; margins >=10%)')
# WL
for i,(v,rel,rel2,gr,n,lam,lamc) in wl.items():
    amb='none'; conf='high'
    if gr<=0:
        amb='no admissible mode has positive growth; "fastest-growing" interpreted as max Re(lambda) (least damped). Under a reading that there is no growing mode, no wavelength is defined and the formula cannot be said to be adequate (still out_of_scope).'; conf='medium'
    if i=='wl-0010':
        amb='near-tie: n=9 growth .23062 vs n=8 .22994; n=8 would give 5.4% error (applies). Exact max picks n=9.'; conf='medium'
    put(i,v,conf,f'argmax_n Re lambda(q_n), q_n=(n/L*)^2: n={n}, lambda={lam:.4f}, lambda_c={lamc:.4f}, rel err {rel:.4f} (vs lam: {rel2:.4f}); max growth {gr:.5f}',amb)
# KP
for l in ids:
    i=l['id']
    if not i.startswith('kp'): continue
    t=l['request_text'][:l['request_text'].find('Conventions:')]
    if 'saturating growth term' in t: put(i,'underdetermined','high','growth term not specified (unknown); speed 2sqrt(sD) holds only for linearly determined (pulled) kinetics','none'); continue
    if 'logistic' in t: put(i,'applies','high','logistic = KPP: c*=2 sqrt(sD)','none'); continue
    if re.search(r'bistable|strong-Allee',t):
        th=re.search(r'\(u ?- ?(\d+/\d+)\)',t).group(1)
        put(i,'out_of_scope','high',f'strong Allee threshold theta={th}<1/2: front invades with pushed speed sqrt(sD/2)(1-2theta) != 2 sqrt(sD)','none'); continue
    m=re.search(r'\(1 ?\+ ?(\d+(?:/\d+)?)(?:\*)?u\)',t) or re.search(r'1 ?\+ ?(\d+/\d+)\*u',t) or re.search(r'1\+(\d+/\d+)u',t)
    a=F(m.group(1))
    if a<2: put(i,'applies','medium',f'f=su(1-u)(1+{a}u): f\'(0)=s; pulled for alpha<=2 (exact front c=(2+a)/sqrt(2a) valid only for a>=2), so speed=2sqrt(sD)',f'not KPP-bounded (alpha>1, f(u)/u exceeds f\'(0)) but still linearly determined for alpha<2; a reader using the KPP inequality f<=f\'(0)u would say out_of_scope')
    elif a==2: put(i,'applies','medium','alpha=2 exactly: critical, c=(2+2)/sqrt(4)=2 => 2sqrt(sD) exactly (pulled/pushed transition)','marginal case alpha=2; non-KPP but speed equals 2sqrt(sD); KPP-inequality reader would say out_of_scope')
    else: put(i,'out_of_scope','high',f'alpha={a}>2: pushed front, c=(2+a)/sqrt(2a)*sqrt(sD) > 2 sqrt(sD)','none')
for v in V.values():
    if v['ambiguity'].startswith('none'): v['ambiguity']='none'
    if v['ambiguity'].startswith('g not stated (assumed 9.81; margins >=10%)'): v['ambiguity']='none material (g not stated; 9.81 assumed, verdict insensitive)'
assert len(V)==136, len(V)
with open('blind_verdicts.jsonl','w') as f:
    for i in sorted(V): f.write(json.dumps(V[i])+'\n')
import collections
print(collections.Counter(v['verdict'] for v in V.values()))
for i in sorted(V):
    v=V[i]
    if v['confidence']!='high' or v['ambiguity']!='none': print(i,v['verdict'],v['confidence'],'|',v['ambiguity'][:140])
