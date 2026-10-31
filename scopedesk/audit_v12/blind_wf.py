import re,json
from fractions import Fraction as F
import mpmath as mp
from blind_common import *
mp.mp.dps=50
def exact(N,s):
    s=mp.mpf(s.numerator)/s.denominator
    A=mp.zeros(N-1,N-1); b=mp.zeros(N-1,1)
    for i in range(1,N):
        p=i*(1+s)/(i*(1+s)+N-i)
        for j in range(0,N+1):
            pr=mp.binomial(N,j)*p**j*(1-p)**(N-j)
            if j==N: b[i-1]+=pr
            elif j>=1: A[i-1,j-1]-=pr
        A[i-1,i-1]+=1
    h=mp.lu_solve(A,b)
    return h[0]
res={}
for d in load():
    p=d['prompt']
    if 'Wright-Fisher population of N' not in p: continue
    pl=p[:p.find('Conventions:')]
    m=re.search(r'N = (\d+)',pl) or re.search(r'population of (\d+) haploid',pl) or re.search(r'Population size (\d+)',pl) or re.search(r'N = (\d+)',pl)
    N=int(m.group(1))
    m=re.search(r's = ('+NUM+')',pl) or re.search(r'1 \+ ('+NUM+')',pl) or re.search(r'advantage ('+NUM+')',pl)
    s=F(m.group(1))
    ex=exact(N,s)
    if 'Kimura' in pl and 'neutral' in pl or 'simply 1/' in pl: appr=mp.mpf(1)/N; kind='neutral'
    else:
        sm=mp.mpf(s.numerator)/s.denominator
        appr=(1-mp.e**(-2*sm))/(1-mp.e**(-2*N*sm)); kind='kimura'
    rel=abs(appr-ex)/ex
    v='applies' if rel<=mp.mpf('0.1') else 'out_of_scope'
    print(d['id'],kind,N,s,mp.nstr(ex,8),mp.nstr(appr,8),mp.nstr(rel,6),v)
    res[d['id']]=dict(v=v,rel=float(rel),kind=kind)
json.dump(res,open('blind_wf_out.json','w'))
