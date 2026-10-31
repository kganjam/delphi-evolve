import re,json,math
from fractions import Fraction as F
from blind_common import *

def terms(expr):
    cu=cv=F(0)
    for sg,num,var in re.findall(r'([+-]?)\s*(\d+(?:/\d+)?)\s*([uv])\b',expr):
        val=F(num)*(-1 if sg=='-' else 1)
        if var=='u': cu+=val
        else: cv+=val
    return cu,cv

def parse_J(p):
    m=re.search(r'J = \[\[('+NUM+r'), ('+NUM+r')\], \[('+NUM+r'), ('+NUM+r')\]\]',p)
    if m: return [F(x) for x in m.groups()]
    m=re.search(r'rows \(('+NUM+r'), ('+NUM+r')\) and \(('+NUM+r'), ('+NUM+r')\)',p)
    if m: return [F(x) for x in m.groups()]
    m=re.search(r'Self-feedback of u is ('+NUM+r'), cross-effect of v on u is ('+NUM+r'), effect of u on v is ('+NUM+r'), self-feedback of v is ('+NUM+r')',p)
    if m: return [F(x) for x in m.groups()]
    m=re.search(r"u' = ([^,]*), v' = ([^.]*)\.",p)
    if m:
        a,b=terms(m.group(1)); c,d=terms(m.group(2)); return [a,b,c,d]
    m=re.search(r'f_u = (.*?) and g = (.*?) around',p) or re.search(r'f_u = (.*?), g = (.*?);',p) or re.search(r'f_u = (.*?) and g = (.*?)(?:,|\.)',p)
    if m:
        a,b=terms(m.group(1)); c,d=terms(m.group(2)); return [a,b,c,d]
    raise ValueError('J')

def parse_Dv(p):
    m=re.search(r'D_v = ('+NUM+')',p)
    if m: return F(m.group(1))
    m=re.search(r'diffusivity set to ('+NUM+')',p)
    if m: return F(m.group(1))
    m=re.search(r'('+NUM+r') times (?:faster|as diffusive)',p)
    if m: return F(m.group(1))
    raise ValueError('Dv')

def lenfrac(s):
    s=s.strip()
    return s

def parse_len(p):
    # returns list of candidate lengths (multiples of pi) 
    m=re.search(r'length is ('+NUM+r') times pi',p) or re.search(r'length ('+NUM+r')\*pi',p) \
      or re.search(r'length L = ('+NUM+r')π',p) or re.search(r'length (?:is )?(?:of )?('+NUM+r')\*pi',p) \
      or re.search(r'domain length to be pi x ('+NUM+')',p) or re.search(r'length pi x ('+NUM+')',p) \
      or re.search(r'whose length is ('+NUM+r')\*pi',p)
    if m: return [F(m.group(1))]
    m=re.search(r'length L = 1/2π',p)
    if m: return [F(1,2),F(2)]  # (1/2)pi vs 1/(2pi) -> special
    m=re.search(r'length L = 2π',p)
    return None

def parse_bc(p):
    pl=p[:p.find('Conventions:')]
    if re.search(r'Neumann|no-flux|zero-flux|sealed|reflecting',pl): return 'N'
    if re.search(r'Dirichlet|clamped|held at zero',pl): return 'D'
    if re.search(r'\b(periodic|ring|loop|torus|wrapped)\b',pl): return 'P'
    return None

def analyse(Jm,Dv,Du=F(1)):
    a,b,c,d=Jm
    tr=a+d; det=a*d-b*c
    stable=(tr<0 and det>0)
    S=Dv*a+Du*d
    ineq=(S>0 and S*S>4*Du*Dv*det)  # S>2 sqrt(DuDv det)
    return tr,det,stable,S,ineq

def grows(Jm,Dv,qs):
    a,b,c,d=Jm; det=a*d-b*c; S=Dv*a+d
    for q in qs:
        h=Dv*q*q-S*q+det
        if h<0: return True,q
    return False,None

def interval_q(Lc,bc,N=5000):
    if bc=='P': return [(2*F(n)/Lc)**2 for n in range(1,N)]
    return [(F(n)/Lc)**2 for n in range(1,N)]

def rect_q(a,b,bc,N=400):
    k=1 if bc=='N' else 2
    qs=set()
    for m in range(N):
        for n in range(N):
            if m==0 and n==0: continue
            qs.add((k*F(m)/a)**2+(k*F(n)/b)**2)
    return sorted(qs)
