import re,json
from fractions import Fraction as F
from blind_common import *
from blind_ddi import *
rows=load()
out={}
def interval_len(p):
    pl=p[:p.find('Conventions:')]
    pats=[r'length is ('+NUM+r') times pi', r'length ('+NUM+r')\*pi', r'length L = ('+NUM+r')π', r'to be pi x ('+NUM+r')', r'length pi x ('+NUM+')',r'length of ('+NUM+r')\*pi',r'length L = (1/2)π']
    for pt in pats:
        m=re.search(pt,pl)
        if m: return F(m.group(1)),pt
    m=re.search(r'length L = 2π',pl)
    if m: return F(2),'2π'
    return None,None
for d in rows:
    p=d['prompt']
    if 'diffusion-driven mode on this' not in p: continue
    Jm=parse_J(p); Dv=parse_Dv(p); bc=parse_bc(p)
    tr,det,stable,S,ineq=analyse(Jm,Dv)
    if 'rectangle' in p[p.find('Conventions:'):p.find('Conventions:')+200]:
        pl=p[:p.find('Conventions:')]
        m=re.search(r'size pi x ('+NUM+r') by pi x ('+NUM+')',pl) or re.search(r'sides ('+NUM+r')\*pi and ('+NUM+r')\*pi',pl)
        a,b=F(m.group(1)),F(m.group(2))
        info=dict(kind='rect',a=a,b=b)
        res={}
        for t in ['N','P']:
            res[t]=grows(Jm,Dv,rect_q(a,b,t))[0]
    else:
        L,pt=interval_len(p)
        info=dict(kind='int',L=L)
        res={}
        for t in ['N','P']:
            res[t]=grows(Jm,Dv,interval_q(L,t))[0]
        if 'L = 1/2π' in p: 
            L2=F(1,4)  # 1/(2pi) in units of pi -> 1/(2 pi^2)... handle separately
            info['alt']=True
    res['D']=res.get('N')
    print(d['id'],info.get('kind'),[str(x) for x in Jm],'Dv',Dv,'L' if info['kind']=='int' else 'ab',info.get('L') or (info.get('a'),info.get('b')),'bc',bc,'stable',stable,'tr',tr,'det',det,'ineq',ineq,'grows',res)
    out[d['id']]=dict(Jm=[str(x) for x in Jm],Dv=str(Dv),bc=bc,stable=stable,ineq=ineq,grows=res,info={k:str(v) for k,v in info.items()})
json.dump(out,open('blind_ddi_out.json','w'))
