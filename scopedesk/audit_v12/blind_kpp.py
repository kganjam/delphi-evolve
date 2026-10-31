import re,json,math
from fractions import Fraction as F
from blind_common import *
res={}
for d in load():
    p=d['prompt']; i=d['id']
    if 'asymptotic speed' not in p: continue
    pl=p[:p.find('Conventions:')]
    if 'saturating' in pl or not re.search(r'u\(1-u\)|u\*\(1-u\)',pl):
        v='underdetermined'; n='growth term unspecified'
    else:
        m=re.search(r'u\(1-u\)\(1\+\s*('+NUM+r')u\)',pl) or re.search(r'u\*\(1-u\)\*\(1 \+ ('+NUM+r')\*u\)',pl)
        if m:
            al=F(m.group(1)); v='out_of_scope' if al>2 else 'applies'; n='alpha=%s'%al
        elif re.search(r'\(u ?- ?('+NUM+r')\)',pl):
            a=F(re.search(r'\(u ?- ?('+NUM+r')\)',pl).group(1)); v='out_of_scope'; n='bistable a=%s speed factor (1-2a)/sqrt2 vs 2'%a
            assert a<F(1,2)
        elif 'logistic' in pl: v='applies'; n='logistic'
        else: v='??'; n=''
    print(i,v,n); res[i]=dict(v=v,note=n)
json.dump(res,open('blind_kpp_out.json','w'))
