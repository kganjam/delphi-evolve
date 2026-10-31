import json,re,math
from fractions import Fraction as F
from mpmath import mp,mpf,exp
mp.dps=40
from math import comb
def exact(N,s):
    # states 0..N ; P_i = prob next count = j
    w=1+s
    ps=[F(i)*w/(F(i)*w+N-i) if i>0 else F(0) for i in range(N+1)]
    # solve phi_i = sum_j T_ij phi_j, phi_0=0, phi_N=1 with fractions (gauss)
    n=N-1
    A=[[F(0)]*n for _ in range(n)]; bvec=[F(0)]*n
    for ii in range(1,N):
        p=ps[ii]
        row=ii-1
        A[row][row]+=1
        for j in range(0,N+1):
            t=F(comb(N,j))*p**j*(1-p)**(N-j)
            if j==N: bvec[row]+=t
            elif j>=1: A[row][j-1]-=t
    # gauss
    M=[A[i]+[bvec[i]] for i in range(n)]
    for c in range(n):
        piv=next(r for r in range(c,n) if M[r][c]!=0); M[c],M[piv]=M[piv],M[c]
        pv=M[c][c]; M[c]=[v/pv for v in M[c]]
        for r in range(n):
            if r!=c and M[r][c]!=0:
                f=M[r][c]; M[r]=[a-f*b for a,b in zip(M[r],M[c])]
    return M[0][n]
res={}
for l in open('blind_input.jsonl'):
    x=json.loads(l); i=x['id']
    if not i.startswith('km'): continue
    t=x['request_text'][:x['request_text'].find('Conventions:')]
    if 'Population size' in t:
        N=int(re.search(r'Population size (\d+)',t).group(1)); s=F(re.search(r'advantage (\d+/\d+|\d+)',t).group(1)); kind='diff'
    elif 'population of N' in t:
        N=int(re.search(r'N = (\d+)',t).group(1)); s=F(re.search(r's = (\d+/\d+|\d+)',t).group(1)); kind='diff' if 'Kimura\'s diffusion' in t else 'neutral'
    elif 'In a population of' in t:
        N=int(re.search(r'population of (\d+)',t).group(1)); s=F(re.search(r'1 \+ (\d+/\d+|\d+)',t).group(1)); kind='neutral'
    else: raise Exception(i)
    if 'selection coefficient' in t and "Kimura's diffusion" in t: kind='diff'
    elif 'neutral' in t or 'simply 1/' in t: kind='neutral'
    ex=exact(N,s)
    sf=mpf(s.numerator)/s.denominator
    if kind=='diff': ap=(1-exp(-2*sf))/(1-exp(-2*N*sf))
    else: ap=mpf(1)/N
    exm=mpf(ex.numerator)/ex.denominator
    rel=(ap-exm)/exm
    v='applies' if abs(rel)<=mpf('0.1') else 'out_of_scope'
    print(i,kind,N,s,'exact',float(exm),'approx',float(ap),'rel',float(rel),v)
    res[i]=(v,float(rel),kind)
json.dump(res,open('blind_km_out.json','w'))
