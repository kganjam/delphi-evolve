import re,json
from fractions import Fraction as F
import mpmath as mp
from blind_common import *
from blind_ddi import parse_J,parse_Dv
mp.mp.dps=40
res={}
for d in load():
    p=d['prompt']; i=d['id']
    if 'linear analysis only' not in p: continue
    pl=p[:p.find('Conventions:')]
    Jm=parse_J(pl+'.' ) if 'Jacobian [[' not in pl else None
    if Jm is None:
        m=re.search(r'Jacobian \[\[('+NUM+r'), ('+NUM+r')\], \[('+NUM+r'), ('+NUM+r')\]\]',pl); Jm=[F(x) for x in m.groups()]
    Dv=parse_Dv(pl)
    m=re.search(r'length (?:of )?('+NUM+r')\*pi',pl) or re.search(r'length pi x ('+NUM+')',pl)
    L=F(m.group(1))
    a,b,c,dd=Jm; det=a*dd-b*c; tr=a+dd
    kc2=mp.sqrt(mp.mpf(det.numerator)/det.denominator/(mp.mpf(Dv.numerator)/Dv.denominator))
    lam_c=2*mp.pi/mp.sqrt(kc2)
    best=None; rows=[]
    for n in range(1,3000):
        q=mp.mpf(n*n)/(L*L)  # (n pi/L_phys)^2 with L_phys=L*pi
        Jq=mp.matrix([[a-q,b],[c,dd-Dv*q]]) if False else None
        T=mp.mpf(tr.numerator)/tr.denominator - q*(1+mp.mpf(Dv.numerator)/Dv.denominator)
        h=(mp.mpf(Dv.numerator)/Dv.denominator)*q*q-(mp.mpf((Dv*a+dd).numerator)/(Dv*a+dd).denominator)*q+mp.mpf(det.numerator)/det.denominator
        disc=T*T-4*h
        re_l=(T+mp.sqrt(disc))/2 if disc>=0 else T/2
        if re_l>0:
            rows.append((n,re_l))
        if q>50 and not rows: break
        if q>1e4: break
    if not rows:
        v='out_of_scope'; n_=None; rel=None
    else:
        n_,g=max(rows,key=lambda t:t[1])
        wl=2*mp.pi*L*mp.pi/(n_*mp.pi)  # 2pi/sqrt(q) = 2 L_phys/n = 2 L pi/n
        wl=2*L*mp.pi/n_
        rel=abs(wl-lam_c)/lam_c
        v='applies' if rel<=mp.mpf('0.1') else 'out_of_scope'
    print(i,'tr',tr,'det',det,'Dv',Dv,'L',L,'growing modes',[r[0] for r in rows][:8],'best',n_,'rel',mp.nstr(rel,6) if rel is not None else None,v)
    res[i]=dict(v=v,rel=float(rel) if rel is not None else None,best=n_,nmodes=len(rows),tr=str(tr))
json.dump(res,open('blind_wave_out.json','w'))
