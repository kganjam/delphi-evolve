import json,re
from fractions import Fraction as F
import mpmath as mp
mp.mp.dps=40
NUM=r'(-?\d+(?:/\d+)?)'
SG=r'([+-])'
res={}
for l in open('blind_input.jsonl'):
    x=json.loads(l); i=x['id']
    if not i.startswith('wl'): continue
    t=x['request_text'][:x['request_text'].find('Conventions:')]
    m=re.search(r'Jacobian \[\[%s, %s\], \[%s, %s\]\]'%((NUM,)*4),t)
    if m: J=[F(v) for v in m.groups()]
    else:
        m=re.search(r'f_u = %su %s %sv, g = %su %s %sv'%(NUM,SG,r'(\d+(?:/\d+)?)',NUM,SG,r'(\d+(?:/\d+)?)'),t)
        a,s1,b,c,s2,d=m.groups(); J=[F(a),F(b)*(1 if s1=='+' else -1),F(c),F(d)*(1 if s2=='+' else -1)]
    m=re.search(r'D_v = (\d+(?:/\d+)?)',t) or re.search(r'second species is (\d+(?:/\d+)?) times',t); Dv=F(m.group(1))
    m=re.search(r'length (\d+)\*pi',t) or re.search(r'pi x (\d+)',t); L=int(m.group(1))   # in units of pi
    a,b,c,d=J; det=a*d-b*c; tr=a+d
    kc2=mp.sqrt(mp.mpf(det.numerator)/det.denominator/(mp.mpf(Dv.numerator)/Dv.denominator))
    lamc=2*mp.pi/mp.sqrt(kc2)
    def growth(q):
        A=mp.matrix([[mp.mpf(a.numerator)/a.denominator-q, mp.mpf(b.numerator)/b.denominator],[mp.mpf(c.numerator)/c.denominator, mp.mpf(d.numerator)/d.denominator-q*mp.mpf(Dv.numerator)/Dv.denominator]])
        T=A[0,0]+A[1,1]; De=A[0,0]*A[1,1]-A[0,1]*A[1,0]
        disc=T*T-4*De
        if disc>=0: return (T+mp.sqrt(disc))/2
        return T/2
    rows=[]
    for n in range(1,4000):
        q=(mp.mpf(n)/L)**2   # (n pi / (L pi))^2
        rows.append((growth(q),n))
    rows.sort(key=lambda z:-z[0])
    best=rows[0]; second=rows[1]
    n=best[1]; lam=2*mp.pi/mp.sqrt((mp.mpf(n)/L)**2)  # 2L pi/n
    rel=abs(lam-lamc)/lamc
    # nearest-mode alternatives
    nc=L*mp.pi*2/lamc  # continuous n for lam_c: n = 2L/lambda * pi.. 
    stable=(tr<0 and det>0)
    print(i,'det',det,'tr',tr,'stable',stable,'ineq',(Dv*a+d)**2>4*Dv*det and Dv*a+d>0,'kc',float(mp.sqrt(kc2)),'lamc',float(lamc),'L/pi',L,'best n',n,'growth',mp.nstr(best[0],8),'2nd',second[1],mp.nstr(second[0],8),'lam',float(lam),'rel',float(rel),'n_c',float(nc/ mp.pi*mp.pi) )
    v='applies' if rel<=mp.mpf('0.1') else 'out_of_scope'
    # also alternate reading: relative to lam
    rel2=abs(lam-lamc)/lam
    res[i]=(v,float(rel),float(rel2),float(best[0]),n,float(lam),float(lamc))
    print('   ->',v,'rel to lam:',float(rel2),'max growth',float(best[0]))
json.dump(res,open('blind_wl_out.json','w'))
