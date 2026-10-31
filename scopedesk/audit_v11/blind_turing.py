import json,re
from fractions import Fraction as F
r=[json.loads(l) for l in open('blind_input.jsonl')]
def fr(s):
    s=s.strip()
    return F(s)
NUM=r'(-?\d+(?:/\d+)?)'
def parse(t):
    body=t[:t.find('Conventions:')]
    d={}
    m=re.search(r'J = \[\[%s, %s\], \[%s, %s\]\]'%((NUM,)*4),body)
    if m: J=[fr(x) for x in m.groups()]
    else:
        m=re.search(r'rows \(%s, %s\) and \(%s, %s\)'%((NUM,)*4),body)
        if m: J=[fr(x) for x in m.groups()]
        else:
            m=re.search(r'f_u = %su %s %sv and g = %su %s %sv'%(NUM,r'([+-])',r'(\d+(?:/\d+)?)',NUM,r'([+-])',r'(\d+(?:/\d+)?)'),body)
            if m:
                a,s1,b,c,s2,dd=m.groups(); J=[fr(a),fr(b)*(1 if s1=='+' else -1),fr(c),fr(dd)*(1 if s2=='+' else -1)]
            else:
                m=re.search(r"u' = %su %s %sv, v' = %su %s %sv"%(NUM,r'([+-])',r'(\d+(?:/\d+)?)',NUM,r'([+-])',r'(\d+(?:/\d+)?)'),body)
                if m:
                    a,s1,b,c,s2,dd=m.groups(); J=[fr(a),fr(b)*(1 if s1=='+' else -1),fr(c),fr(dd)*(1 if s2=='+' else -1)]
                else:
                    m=re.search(r'Self-feedback of u is %s, cross-effect of v on u is %s, effect of u on v is %s, self-feedback of v is %s'%((NUM,)*4),body)
                    J=[fr(x) for x in m.groups()]
    # Dv
    m=re.search(r'D_v = (\d+(?:/\d+)?)',body) or re.search(r'(\d+(?:/\d+)?) times (?:as diffusive|faster)',body) or re.search(r'diffusivity set to (\d+(?:/\d+)?)',body)
    Dv=fr(m.group(1))
    return J,Dv,body
def bc(body):
    b=body.lower()
    if 'dirichlet' in b or 'held at zero' in b or 'clamped' in b: return 'D'
    if 'no-flux' in b or 'zero-flux' in b or 'sealed' in b or 'reflecting' in b: return 'N'
    if 'periodic' in b or re.search(r'\bring\b',b) or 'loop' in b or 'torus' in b: return 'P'
    return None
def length(body):
    m=re.search(r'L = (\d+(?:/\d+)?)π',body) or re.search(r'length (?:of )?(\d+(?:/\d+)?)\*pi',body) or re.search(r'length (\d+(?:/\d+)?)\*pi',body) or re.search(r'whose length is (\d+(?:/\d+)?) times pi',body) or re.search(r'pi x (\d+(?:/\d+)?)',body) 
    if not m: m=re.search(r'L = (\d+)/(\d+)π',body)
    return fr(m.group(1))
def hneg(J,Dv,q):
    a,b,c,d=J
    return Dv*q*q-(Dv*a+d)*q+(a*d-b*c)
def analyse(J,Dv,qs):
    a,b,c,d=J; det=a*d-b*c; tr=a+d
    ineq=(Dv*a+d)>0 and (Dv*a+d)**2>4*Dv*det  # equivalent to > 2 sqrt(Dv det)
    stable=(tr<0 and det>0)
    unst=[q for q in qs if hneg(J,Dv,q)<0]
    zero=[q for q in qs if hneg(J,Dv,q)==0]
    return dict(det=det,tr=tr,ineq=ineq,stable=stable,unst=bool(unst),zero=bool(zero))
out={}
for x in sorted(r,key=lambda x:x['id']):
    i=x['id']
    if not i.startswith(('ts','t2')): continue
    J,Dv,body=parse(x['request_text'])
    if i.startswith('ts'):
        L=length(body); B=bc(body)
        def qsets(B):
            if B=='P': return [ (2*n/L)**2 for n in range(1,3000)]
            return [(n/L)**2 for n in range(1,3000)]
        res={}
        for BB in ('D','N','P'): res[BB]=analyse(J,Dv,qsets(BB))
        print(i,'J',[str(v) for v in J],'Dv',Dv,'L/pi',L,'bc',B,'| ineq',res['N']['ineq'],'stable',res['N']['stable'],'unst D/N/P',res['D']['unst'],res['N']['unst'],res['P']['unst'],'zero',res['D']['zero'] and 'Z',res['P']['zero'] and 'Z')
        out[i]=dict(J=[str(v) for v in J],Dv=str(Dv),L=str(L),bc=B,res=res)
    else:
        m=re.search(r'sides (\d+(?:/\d+)?)\*pi and (\d+(?:/\d+)?)\*pi',body) or re.search(r'size pi x (\d+(?:/\d+)?) by pi x (\d+(?:/\d+)?)',body)
        a_,b_=fr(m.group(1)),fr(m.group(2)); B=bc(body)
        res={}
        for BB in ('N','P'):
            k=1 if BB=='N' else 2
            qs=[(k*mm/a_)**2+(k*nn/b_)**2 for mm in range(0,200) for nn in range(0,200) if mm+nn>0]
            res[BB]=analyse(J,Dv,qs)
        print(i,'J',[str(v) for v in J],'Dv',Dv,'a,b',a_,b_,'bc',B,'| ineq',res['N']['ineq'],'stable',res['N']['stable'],'unst N/P',res['N']['unst'],res['P']['unst'],'zero',res['N']['zero'] and 'Z',res['P']['zero'] and 'Z')
        out[i]=dict(J=[str(v) for v in J],Dv=str(Dv),a=str(a_),b=str(b_),bc=B,res=res)
json.dump(out,open('blind_turing_out.json','w'),indent=1,default=str)
