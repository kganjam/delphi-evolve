import math, mpmath as mp
from audit_common import *
rows=load(); out=[]
def add(r,v,conf,rule,notes=''):
    out.append(dict(id=r['id'],family=r['family'],verdict=v,confidence=conf,rule=rule,notes=notes))
# ---------- Greenhill constant check
z=mp.findroot(lambda x: mp.besselj(mp.mpf(-1)/3,x),1.87)
print('J_{-1/3} first zero',z,'9/4 z^2 =',9*z*z/4)
g=9.81
for r in rows:
    s=r['structured']; fam=r['family']
    if fam=='rayleigh_plateau':
        sv=F(s['s']); bc=s['bc']
        crit_pred = sv>2           # cited criterion l>2 pi r
        def exact(bc):
            # kr<1 for admissible k. periodic: k=2 pi n / l = 2n/(s r); pinned: k=n pi/l = n/(s r)
            if bc=='periodic': return any(F(2*n)/sv<1 for n in range(1,int(sv*4)+3))
            if bc=='pinned': return any(F(n)/sv<1 for n in range(1,int(sv*4)+3))
        if bc:
            ex=exact(bc); agree=(ex==crit_pred)
            add(r,'applies' if agree else 'out_of_scope','medium' if (bc=='pinned' and agree) else 'high',
                f"{bc}: exact unstable={ex} (k r<1 for some admissible mode; true threshold s>{'2' if bc=='periodic' else '1'}), cited l>2 pi r predicts {crit_pred}",
                'pinned with s>2: conclusion (unstable) agrees but the threshold itself is wrong for pinned ends (true threshold l>pi r); scored by outcome-agreement' if (bc=='pinned' and agree) else '')
        else:
            e={b:exact(b) for b in('periodic','pinned')}
            ag={b:(e[b]==crit_pred) for b in e}
            if len(set(ag.values()))==1:
                add(r,'applies' if all(ag.values()) else 'out_of_scope','medium','bc unstated; completions agree '+str(e))
            else:
                add(r,'underdetermined','high',f"bc unstated; periodic exact={e['periodic']} (criterion right), pinned exact={e['pinned']} (criterion wrong); cited predicts {crit_pred}. Missing: end condition")
    elif fam=='hawk_dove_ess':
        V=F(s['V']); C=fr(s['C'])
        if C is None:
            add(r,'underdetermined','high',f"C unstated: C>V gives ESS mixed p=V/C (applies), C<=V gives pure Hawk (formula would give p>=1). Missing: cost C")
        else:
            # EHH=(V-C)/2. Hawk is strict ESS iff E(H,H)>E(D,H) i.e. (V-C)/2>0 ; mixed ESS iff C>V
            if C>V: add(r,'applies','high',f"C={C}>V={V}: mixed ESS p*=V/C={V/C} in (0,1); check E(H,H)<E(D,H)=0 and E(D,D)<E(H,D)")
            elif C<V: add(r,'out_of_scope','high',f"C={C}<V={V}: E(H,H)=(V-C)/2>0=E(D,H), Hawk is pure strict ESS; V/C={V/C}>1 is not a probability")
            else: add(r,'out_of_scope','low','C==V degenerate')
    elif fam=='greenhill_buckling':
        D=s['D'];E=s['E'];H=s['H'];rho=s['rho'];t=s['t']
        if t!=1.0:
            note=''
            if rho is None: note='rho also missing but taper violation already decides'
            res=''
            if rho: 
                Hc=(7.8373*E*(math.pi*D**4/64)/(rho*g*math.pi*D**2/4))**(1/3); res=f" (uniform-formula Hcr={Hc:.2f} vs H={H}, ratio {H/Hc:.3f}; would be misleading since taper changes critical height)"
            add(r,'out_of_scope','high' if rho else 'medium',f"taper t={t}!=1: Greenhill uniform-column formula not licensed"+res,note)
        elif rho is None:
            add(r,'underdetermined','medium',"uniform but density rho missing; Hcr ~ rho^(-1/3); missing: rho (task rule). Plausible-density completions: see notes",
                 'Hcr(rho=300..2500) range: '+', '.join(f"{rr}:{(7.8373*E*(D*D/16)/(rr*g))**(1/3):.1f}" for rr in (300,600,800,1000,1500,2500))+f" vs H={H}")
        else:
            Hc=(7.8373*E*(D**2/16)/(rho*g))**(1/3)
            add(r,'applies','high',f"uniform, fixed base, rho given: Hcr=(7.8373 E I/(rho g A))^(1/3)={Hc:.2f} m vs H={H}; ratio {H/Hc:.3f}; buckles={H>Hc}",
                'BORDERLINE (<3% of Hcr)' if abs(H/Hc-1)<0.03 else '')
    elif fam=='hamilton_rule_form':
        b,c,rr,d=F(s['b']),F(s['c']),F(s['r']),F(s['d']); p=fr(s['p'])
        hamilton = rr*b-c>0
        def delta(p): return rr*b-c+d*(rr+(1-rr)*p)
        if d==0:
            add(r,'applies','high',f"additive (d=0): carrier-minus-noncarrier payoff = rb-c={rr*b-c}; independent of p")
        elif p is not None:
            dl=delta(p); truth=dl>0
            if truth==hamilton: add(r,'applies','medium',f"d={d}!=0, p={p}: true advantage rb-c+d(r+(1-r)p)={dl}; sign agrees with Hamilton (rb-c={rr*b-c}) at this p only",'non-additive but outcome coincides; scored by outcome-agreement. Would flip at other p: '+str(delta(F(0))>0)+'/'+str(delta(F(1))>0)+' at p=0/1')
            else: add(r,'out_of_scope','high',f"d={d}!=0, p={p}: true advantage {dl} (>0 is {truth}); Hamilton predicts {hamilton}: disagree")
        else:
            lo,hi=sorted([delta(F(0)),delta(F(1))])
            if lo>0 or hi<0:
                tr=lo>0
                add(r,'applies' if tr==hamilton else 'out_of_scope','medium',f"p unstated, advantage range [{lo},{hi}] sign-definite")
            else:
                add(r,'underdetermined','high',f"p unstated; true advantage ranges [{lo},{hi}] across p in [0,1] crossing 0; Hamilton predicts {hamilton}. Missing: frequency p")
    elif fam=='fisher_kpp_speed':
        k=s['kind']; par=fr(s['par'])
        if k=='logistic': add(r,'applies','high','f=u(1-u): KPP, c*=2 sqrt(sD) for compact data')
        elif k=='unspecified': add(r,'underdetermined','high','growth form unstated: logistic -> 2sqrt(sD) holds, bistable/pushed -> fails. Missing: f(u)')
        elif k=='allee':
            c=lambda: math.sqrt(float(F(s['s'])*F(s['D']))/2)*(1-2*float(par))
            add(r,'out_of_scope','high',f"strong Allee a={par}: pushed/bistable speed sqrt(sD/2)(1-2a)={c():.3f} vs cited 2sqrt(sD)={2*math.sqrt(float(F(s['s'])*F(s['D']))):.3f}")
        elif k=='cubic_pos':
            if par<=2: add(r,'applies','high' if par<2 else 'medium',f"f=u(1-u)(1+{par}u): linearly determined (pulled) iff alpha<=2 (exact pushed wave c=(2+a)/sqrt(2a) sqrt(sD) is selected only if decay k^2=s*a/(2D)>s/D i.e. a>2); alpha={par}",
                         'KPP sufficient condition f<=f\'(0)u fails for alpha>1 but front is still pulled for 1<alpha<=2; alpha=2 exactly critical (speed equals 2sqrt(sD))' if par>1 else '')
            else:
                a=float(par); cs=(2+a)/math.sqrt(2*a)*math.sqrt(float(F(s['s'])*F(s['D'])))
                add(r,'out_of_scope','high',f"alpha={par}>2: pushed front c=(2+a)/sqrt(2a) sqrt(sD)={cs:.3f} > 2sqrt(sD)={2*math.sqrt(float(F(s['s'])*F(s['D']))):.3f}")
    else: continue
for o in sorted(out,key=lambda x:x['id']): print(o['id'],o['verdict'],o['confidence'],o['rule'][:200],'|',o['notes'][:120])
save('rest',out)
