import json,re
from fractions import Fraction as F
NUM=r'(-?\d+(?:/\d+)?)'
res={}
for l in open('blind_input.jsonl'):
    x=json.loads(l); i=x['id']; t=x['request_text'][:x['request_text'].find('Conventions:')]
    if i.startswith('hm'):
        m=re.search(r'c = %s'%NUM,t) or re.search(r'costs the helper %s'%NUM,t); c=F(m.group(1))
        m=re.search(r'b = %s'%NUM,t) or re.search(r'gives the recipient %s'%NUM,t); b=F(m.group(1))
        m=re.search(r'r = %s'%NUM,t) or re.search(r'relatedness is %s'%NUM,t); r=F(m.group(1))
        m=re.search(r'synergy of %s'%NUM,t) or re.search(r'bonus of %s'%NUM,t); d=F(m.group(1)) if m else F(0)
        m=re.search(r'frequency (?:is )?%s'%NUM,t); p=F(m.group(1)) if m else None
        rule=r*b-c
        def diff(p): return -c+b*r+d*(r+(1-r)*p)   # w1-w0
        sgn=lambda v:(v>0)-(v<0)
        if p is not None:
            cov=p*(1-p)*diff(p); 
            same = (rule>0)==(cov>0)
            v='applies' if same else 'out_of_scope'
            print(i,'c',c,'b',b,'r',r,'d',d,'p',p,'rule',rule,'covdiff',diff(p),v)
        else:
            lo,hi=diff(F(0)),diff(F(1))  # range of diff over p in [0,1], linear
            sg=[(v>0) for v in (lo,hi)]
            # covariance>0 iff diff>0 for p in (0,1)
            if all(v>0 for v in (lo,hi)): cp='always'
            elif all(v<=0 for v in (lo,hi)): cp='never'
            else: cp='depends'
            if cp=='depends': v='underdetermined'
            else: v='applies' if (cp=='always')==(rule>0) else 'out_of_scope'
            print(i,'c',c,'b',b,'r',r,'d',d,'p None','rule',rule,'diff range',lo,hi,cp,v)
        res[i]=v
    if i.startswith('hd'):
        Vm=re.search(r'V = (\d+(?:/\d+)?)',t) or re.search(r'worth (\d+(?:/\d+)?)',t); V=F(Vm.group(1))
        Cm=re.search(r'C = (\d+(?:/\d+)?)',t) or re.search(r'costs (\d+(?:/\d+)?)',t)
        if not Cm: v='underdetermined'; print(i,V,'C unknown',v)
        else:
            C=F(Cm.group(1)); q=V/C
            v='applies' if q<1 else ('out_of_scope') 
            print(i,V,C,q,v)
        res[i]=v
json.dump(res,open('blind_hmhd_out.json','w'))
