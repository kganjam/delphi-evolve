import math, mpmath as mp
from audit_common import *
mp.mp.dps=50
rows=[r for r in load() if r['family'] in('turing_finite_domain','wavelength_formula_licence')]

def modes(bc, r, nmax):
    # returns list of (n, q) with q = k^2 for admissible modes
    if bc=='neumann': return [(n,(F(n)/r)**2) for n in range(0,nmax)]
    if bc=='dirichlet': return [(n,(F(n)/r)**2) for n in range(1,nmax)]
    if bc=='periodic': return [(n,(2*F(n)/r)**2) for n in range(0,nmax)]
def h(J,Dv,q):
    a,b,c,d=J
    return Dv*q*q-(Dv*a+d)*q+(a*d-b*c)   # det(J-qD), Du=1
def unstable_modes(J,Dv,bc,r):
    a,b,c,d=J
    # window: h<0 only for q below larger root; bound n
    B=(Dv*a+d); det=a*d-b*c
    qmax = float(abs(B)/Dv + 1) + 1
    nmax=int(math.sqrt(qmax)*float(r)*(2 if bc=='periodic' else 1))+5
    ms=modes(bc,r,nmax+int(10*float(r))+5)
    return [n for n,q in ms if h(J,Dv,q)<0]
def analyse(s):
    J=[F(x) for x in s['J']]; Dv=F(s['Dv']); r=F(s['r_over_pi'])
    a,b,c,d=J; tr=a+d; det=a*d-b*c
    stable = tr<0 and det>0
    ddi = (Dv*a+d>0) and ((Dv*a+d)**2>4*Dv*det) and det>0
    return J,Dv,r,tr,det,stable,ddi
out=[]
for rw in rows:
    s=rw['structured']; J,Dv,r,tr,det,stable,ddi=analyse(s)
    rec={'id':rw['id'],'family':rw['family']}
    if rw['family']=='turing_finite_domain':
        res={}
        for bc in ('neumann','dirichlet','periodic'):
            um=unstable_modes(J,Dv,bc,r); res[bc]=um[:6]
        def verdict(bc):
            return 'applies' if (stable and ddi and res[bc]) else 'out_of_scope'
        bc=s['bc']
        notes=f"tr={tr} det={det} stable={stable} DDI_ineq_true={ddi} unstable modes n (first): {res}"
        if bc:
            v=verdict(bc); conf='high'
            rule=f"Du=1; unstable iff det(J-qD)=Dv q^2-(Dv a+d)q+det<0 for admissible q; stable={stable}, ddi={ddi}, modes[{bc}]={res[bc]}"
        else:
            vs={b:verdict(b) for b in res}
            if len(set(vs.values()))==1: v=list(vs.values())[0]; conf='medium'; rule=f"bc unstated but all three BCs give {v}; "+str(res)
            else: v='underdetermined'; conf='high'; rule=f"bc unstated; BC-completions disagree {vs}; missing info: boundary condition"
        if not ddi: notes+=" ** request's DDI claim is FALSE for these numbers **"
        if not stable: notes+=" ** homogeneous state not stable **"
        rec.update(verdict=v,confidence=conf,rule=rule,notes=notes)
    else:
        # Neumann wavelength test
        L=r; um=unstable_modes(J,Dv,'neumann',r)
        if not (stable and um):
            rec.update(verdict='out_of_scope',confidence='high',rule=f"stable={stable} no unstable admissible Neumann mode -> no pattern at all",notes='')
        else:
            best=None
            for n in range(1,int(float(r))*400+50):
                q=mp.mpf(n)**2/mp.mpf(r.numerator)**2*mp.mpf(r.denominator)**2
                a,b,c,d=[mp.mpf(x.numerator)/x.denominator for x in J]
                dv=mp.mpf(Dv.numerator)/Dv.denominator
                A=a-q; Dd=d-dv*q
                t=A+Dd; dt=A*Dd-b*c
                disc=t*t-4*dt
                lam=(t+mp.sqrt(disc))/2 if disc>=0 else t/2
                if best is None or lam>best[0]: best=(lam,n)
            lam,n=best
            wl_true=2*mp.pi*mp.mpf(r.numerator)/r.denominator/n
            dv=mp.mpf(Dv.numerator)/Dv.denominator; detf=mp.mpf(det.numerator)/det.denominator
            kc=(detf/dv)**mp.mpf('0.25'); wl_pred=2*mp.pi/kc
            err=abs(wl_pred-wl_true)/wl_true
            # also continuum-domain fastest mode
            B=Dv*J[0]+J[3]
            licensed = err<=mp.mpf('0.10')
            # onset proximity: (Dv a+d)/(2 sqrt(Dv det))
            prox=float(mp.mpf(B.numerator)/B.denominator/(2*mp.sqrt(dv*detf)))
            rec.update(verdict='applies' if licensed else 'out_of_scope',
                       confidence='high' if abs(float(err)-0.10)>0.03 else 'low',
                       rule=f"wl_pred={float(wl_pred):.4f}; fastest admissible Neumann mode n={n} wl={float(wl_true):.4f}; rel err={float(err):.4f}; criterion ratio B/(2sqrt(Dv det))={prox:.3f}; unstable n={um[:5]}..({len(um)} modes)",
                       notes=('BORDERLINE ' if abs(float(err)-0.10)<=0.03 else '')+f"err={float(err):.4f}")
    out.append(rec)
for r in sorted(out,key=lambda x:x['id']): print(r['id'],r['verdict'],r['confidence'],r['rule'][:230],'|',r['notes'][:150])
save('turing',out)
