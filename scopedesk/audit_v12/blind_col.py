import re,json
from fractions import Fraction as F
from blind_common import *
KC={1.0:7.837347438943962,0.5:12.053559019578543,0.4:13.584238229535185}
g=9.81
res={}
for d in load():
    p=d['prompt']; i=d['id']
    if 'column' not in p: continue
    pl=p[:p.find('Conventions:')]
    m=re.search(r'top diameter is ('+NUM+r') of its base',pl)
    r=float(F(m.group(1))) if m else 1.0
    D=float(re.search(r'base diameter ([\d.]+) m',pl).group(1))
    H=float(re.search(r'(?:standing|height) ([\d.]+) m',pl).group(1))
    E=float(re.search(r'E = ([\d.]+) GPa',pl).group(1))*1e9
    m=re.search(r'density ([\d.]+) kg',pl); rho=float(m.group(1)) if m else None
    if rho is None:
        v='applies' if r==1.0 else 'underdetermined'
        # exact-agreement band in rho
        print(i,'r',r,'D',D,'H',H,'no density ->',v); res[i]=dict(v=v,r=r,note='no density'); continue
    kappa=16*rho*g*H**3/(E*D**2)
    kf=16*0.788**3
    bf=kappa>kf; be=kappa>KC[r]
    v='applies' if bf==be else 'out_of_scope'
    # also alternative formula without rounding: threshold 7.8373 for uniform
    print(i,'r',r,'D',D,'H',H,'E',E/1e9,'rho',rho,'kappa %.4f'%kappa,'form',bf,'exact',be,'kc %.4f'%KC[r],v,'Hf=%.2f Hex=%.2f'%(H*(kf/kappa)**(1/3),H*(KC[r]/kappa)**(1/3)))
    res[i]=dict(v=v,r=r,kappa=kappa)
json.dump(res,open('blind_col_out.json','w'))
