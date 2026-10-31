import json,re
import numpy as np
from scipy.integrate import solve_ivp
from scipy.optimize import brentq
from fractions import Fraction as F
g=9.81
def theta_end(H,r,tol=1e-12):
    # nondimensional: D0=1,E=1, rho*g=1 ; D(s)=r+(1-r)s/H ; I=pi D^4/64 ; A=pi D^2/4 ; W(s)=∫A
    # state: theta, m=EI theta'
    def rhs(s,y):
        th,m=y
        D=r+(1-r)*s/H
        I=np.pi*D**4/64
        # W(s)=∫0^s pi/4 (r+(1-r)σ/H)^2 dσ
        k=(1-r)/H
        if k==0: W=np.pi/4*r*r*s
        else: W=np.pi/4*((r+k*s)**3-r**3)/(3*k)
        return [m/(I), -W*th]
    sol=solve_ivp(rhs,[0,H],[1.0,0.0],rtol=tol,atol=1e-14,method='DOP853')
    return sol.y[0,-1]
def Hcr(r):
    # first H where theta(H)=0
    Hs=np.linspace(0.2,12,240)
    vals=[theta_end(h,r) for h in Hs]
    for a,b,va,vb in zip(Hs[:-1],Hs[1:],vals[:-1],vals[1:]):
        if va>0 and vb<=0:
            return brentq(lambda h:theta_end(h,r,1e-13),a,b,xtol=1e-12)
kap={}
for r in (1.0,0.5,0.4):
    kap[r]=Hcr(r); print('kappa (H_cr/( (E/rho g)^(1/3) D0^(2/3)) ) r=',r,kap[r])
json.dump({str(k):v for k,v in kap.items()},open('blind_gh_kappa.json','w'))
res={}
for l in open('blind_input.jsonl'):
    x=json.loads(l); i=x['id']
    if not i.startswith('gh'): continue
    t=x['request_text'][:x['request_text'].find('Conventions:')]
    D=float(re.search(r'base diameter (\d+(?:\.\d+)?) m',t).group(1))
    H=float(re.search(r'(?:height|standing) (\d+(?:\.\d+)?) m',t).group(1))
    E=float(re.search(r'E = (\d+) GPa',t).group(1))*1e9
    rm=re.search(r'density (\d+) kg',t); rho=float(rm.group(1)) if rm else None
    m=re.search(r'top diameter is (\d+)/(\d+)',t); r=int(m.group(1))/int(m.group(2)) if m else 1.0
    if rho is None:
        print(i,'no density -> underdetermined'); res[i]=('underdetermined',None); continue
    X=(E/(rho*g))**(1/3)*D**(2/3)
    Hu=0.788*X; Hex=kap[r]*X
    bu=H>Hu; be=H>Hex
    print(i,'r',r,'H',H,'H_unif',round(Hu,2),'H_exact',round(Hex,2),'ratio H/Hu',round(H/Hu,4),'H/Hex',round(H/Hex,4),'unifBuckle',bu,'exactBuckle',be,'applies' if bu==be else 'out_of_scope')
    res[i]=('applies' if bu==be else 'out_of_scope',(H/Hu,H/Hex))
json.dump(res,open('blind_gh_out.json','w'))
