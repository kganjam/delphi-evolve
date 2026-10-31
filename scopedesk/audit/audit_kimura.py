import mpmath as mp
from audit_common import *
mp.mp.dps=40
rows=[r for r in load() if r['family']=='kimura_regime']
def wf_fix(N,s):
    # haploid WF: i mutants -> Binomial(N, p_i), p_i=i(1+s)/(i(1+s)+N-i)
    s=mp.mpf(s.numerator)/s.denominator
    n=N-1  # transient states 1..N-1
    A=mp.zeros(n,n); bvec=mp.zeros(n,1)
    for i in range(1,N):
        p=i*(1+s)/(i*(1+s)+N-i)
        for j in range(0,N+1):
            pr=mp.binomial(N,j)*p**j*(1-p)**(N-j)
            if j==N: bvec[i-1]+=pr
            elif j>=1: A[i-1,j-1]-=pr
        A[i-1,i-1]+=1
    x=mp.lu_solve(A,bvec)
    return x[0]
out=[]
for rw in sorted(rows,key=lambda r:r['id']):
    s=rw['structured']; N=s['N']; sv=F(s['s'])
    ex=wf_fix(N,sv); sf=mp.mpf(sv.numerator)/sv.denominator
    if s['kind']=='diffusion':
        ap=(1-mp.e**(-2*sf))/(1-mp.e**(-2*N*sf))
    else: ap=mp.mpf(1)/N
    err=abs(ap-ex)/ex
    ok=err<=mp.mpf('0.10')
    bord=abs(float(err)-0.10)<=0.03
    out.append(dict(id=rw['id'],family='kimura_regime',verdict='applies' if ok else 'out_of_scope',
        confidence='low' if bord else 'high',
        rule=f"exact WF pi1={float(ex):.5f}, approx({s['kind']})={float(ap):.5f}, rel.err={float(err):.4f}, tol 10%",
        notes=('BORDERLINE ' if bord else '')+f"err={float(err):.4f} (borderline = rel err in [7%,13%])"))
    print(out[-1]['id'],out[-1]['verdict'],out[-1]['rule'],'BORD' if bord else '', 'N',N,'s',sv)
save('kimura',out)
