import re,json,math
from fractions import Fraction as F
import mpmath as mp
from blind_common import *
from blind_ddi import terms
res={}
def hd(p):
    pl=p[:p.find('Conventions:')]
    m=re.search(r'V = ('+NUM+')',pl) or re.search(r'worth ('+NUM+')',pl)
    V=F(m.group(1))
    m=re.search(r'C = ('+NUM+')',pl) or re.search(r'costs ('+NUM+')',pl)
    if not m: return V,None,'underdetermined','C missing'
    C=F(m.group(1))
    if V<C: return V,C,'applies','V<C'
    return V,C,'out_of_scope','V>=C'
def ham(p):
    pl=p[:p.find('Conventions:')]
    if 'helper' in pl:
        c=F(re.search(r'costs the helper ('+NUM+')',pl).group(1)); b=F(re.search(r'recipient ('+NUM+')',pl).group(1))
        r=F(re.search(r'relatedness is ('+NUM+')',pl).group(1))
        m=re.search(r'bonus of ('+NUM+')',pl); dd=F(m.group(1)) if m else F(0)
    else:
        c=F(re.search(r'c = ('+NUM+')',pl).group(1)); b=F(re.search(r'b = ('+NUM+')',pl).group(1))
        r=F(re.search(r'r = ('+NUM+')',pl).group(1))
        m=re.search(r'synergy of ('+NUM+')',pl); dd=F(m.group(1)) if m else F(0)
    m=re.search(r'frequency (?:is )?('+NUM+')',pl)
    pf=F(m.group(1)) if m else None
    rule=r*b-c
    rule_pos=rule>0
    if pf is not None:
        exact=-c+r*b+dd*(r+(1-r)*pf)
        ex_pos=exact>0
        return dict(c=c,b=b,r=r,d=dd,p=pf,rule=rule,exact=exact,v='applies' if ex_pos==rule_pos else 'out_of_scope')
    # p unknown
    lo=-c+r*b+dd*r; hi=-c+r*b+dd*1
    if dd==0:
        return dict(c=c,b=b,r=r,d=dd,p=None,rule=rule,v='applies',note='d=0 p irrelevant')
    # exact over p in (0,1): value linear in p between lo (p=0) and hi (p=1), open interval
    # sign set
    signs=set()
    if lo>0 or hi>0: signs.add(True)
    if lo<0 or hi<0: signs.add(False)   # strict interior values
    # nonpositive possible?
    nonpos = (lo<=0 or hi<=0)  # interior could include <=0 values (approx; endpoint exclusion nuance)
    pos = (lo>0 or hi>0)
    return dict(c=c,b=b,r=r,d=dd,p=None,rule=rule,lo=lo,hi=hi,pos_possible=pos,nonpos_possible=nonpos,
         v='underdetermined' if (pos and nonpos) else ('applies' if (pos==rule_pos) else 'out_of_scope'))
for d in load():
    p=d['prompt']; i=d['id']
    if 'Hawk-Dove payoffs' in p:
        V,C,v,n=hd(p); print(i,'HD',V,C,v); res[i]=dict(v=v,note=n)
    elif 'Malthusian' in p:
        r=ham(p); print(i,'HAM',{k:str(x) for k,x in r.items()}); res[i]={k:str(x) for k,x in r.items()}
json.dump(res,open('blind_misc_out.json','w'))
