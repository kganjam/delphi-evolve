import numpy as np
from scipy.integrate import solve_ivp
from scipy.optimize import brentq
def wend(kappa,r):
    f=lambda s:1-(1-r)*s
    # G(s)=int_s^1 f^2 = (f(s)^3 - r^3)/(3(1-r)) for r<1 ; 1-s for r=1
    def G(s):
        if abs(1-r)<1e-14: return 1-s
        return (f(s)**3-r**3)/(3*(1-r))
    def rhs(s,y):
        th,w=y
        return [w/f(s)**4, -kappa*G(s)*th]
    sol=solve_ivp(rhs,[0,1],[0,1],rtol=1e-12,atol=1e-14,method='DOP853')
    return sol.y[1,-1]
def kcr(r):
    ks=np.linspace(0.1,40,800)
    vals=[wend(k,r) for k in ks]
    for i in range(len(ks)-1):
        if vals[i]*vals[i+1]<0:
            return brentq(lambda k:wend(k,r),ks[i],ks[i+1],xtol=1e-12)
for r in [1.0,0.5,0.4]:
    k=kcr(r); print(r,k)
    # equivalent H ratio: kappa ∝ H^3
    print('Hexact/Hformula', (k/(16*0.788**3))**(1/3))
print(16*0.788**3)
