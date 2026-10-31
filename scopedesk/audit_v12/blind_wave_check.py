import re,json
from fractions import Fraction as F
import mpmath as mp
from blind_common import *
from blind_ddi import parse_J,parse_Dv
mp.mp.dps=30
for d in load():
    p=d['prompt']; i=d['id']
    if 'linear analysis only' not in p: continue
    pl=p[:p.find('Conventions:')]
    if 'Jacobian [[' in pl:
        m=re.search(r'Jacobian \[\[('+NUM+r'), ('+NUM+r')\], \[('+NUM+r'), ('+NUM+r')\]\]',pl); Jm=[F(x) for x in m.groups()]
    else: Jm=parse_J(pl+'.')
    Dv=parse_Dv(pl); L=F(re.search(r'length (?:of )?('+NUM+r')\*pi',pl).group(1)) if re.search(r'length (?:of )?('+NUM+r')\*pi',pl) else F(re.search(r'length pi x ('+NUM+')',pl).group(1))
    a,b,c,dd=Jm; det=a*dd-b*c
    best_h=None; best_n=None; cands=[]
    for n in range(1,4000):
        q=F(n*n)/(L*L); h=Dv*q*q-(Dv*a+dd)*q+det
        if h<0: cands.append((h,n))
    lamc=2*mp.pi/mp.sqrt(mp.sqrt(mp.mpf(det.numerator)/det.denominator/(mp.mpf(Dv.numerator)/Dv.denominator)))
    out=[]
    if cands:
        nh=min(cands)[1]
        # closest mode to lamc among growing
        rel=lambda n:abs(2*L*mp.pi/n-lamc)/lamc
        nc=min((n for h,n in cands),key=rel)
        print(i,'minh mode',nh,'rel',mp.nstr(rel(nh),5),'closest growing',nc,mp.nstr(rel(nc),5))
    else: print(i,'no growth')
