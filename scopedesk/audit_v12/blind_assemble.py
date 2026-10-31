import json
from blind_common import load
ddi=json.load(open('blind_ddi_out.json')); wf=json.load(open('blind_wf_out.json'))
misc=json.load(open('blind_misc_out.json')); kpp=json.load(open('blind_kpp_out.json'))
wave=json.load(open('blind_wave_out.json')); col=json.load(open('blind_col_out.json'))
out=[]
for d in load():
    i=d['id']; amb='none'; conf='high'; rule=''; v=None
    if i in ddi:
        x=ddi[i]
        if not x['stable']:
            v='out_of_scope'; rule='base state not strictly stable (trace<0 and det>0 fails)'
            if i in ('q77350570','q17503050'):
                amb='det J = 0 exactly: marginal, not strictly stable; text rule makes it out_of_scope'
        elif x['bc'] is None:
            g=x['grows']; v='underdetermined'; rule='boundary type not stated; Neumann/Dirichlet grows=%s, periodic grows=%s differ'%(g['N'],g['P'])
            amb='boundary unstated; verdict would be applies (N/D) or out_of_scope (periodic) so genuinely boundary-dependent'
        else:
            g=x['grows'][x['bc']]; pred=x['ineq']
            v='applies' if g==pred else 'out_of_scope'
            rule='condition predicts %s; admissible modes on %s domain give growth=%s'%(pred,x['bc'],g)
            if not pred:
                conf='medium'; amb='requester claims the inequality holds but it is false for these numbers; I judged the true condition (predicts no instability, no mode grows) => applies; a reading that treats the requester\'s claim/conclusion as the cited statement would give out_of_scope'
            if i=='q7cf8687e':
                amb='length "1/2π" parses as pi/2 or 1/(2pi); both give no admissible growing mode so verdict invariant'
            if i=='qa5ed7dfd' : amb='length "1/2*pi" read as (1/2)pi; verdict out_of_scope either way'
    elif i in wf:
        x=wf[i]; v=x['v']; rule='exact absorbing-chain fixation prob; relative error %.4f vs 0.10'%x['rel']
        if abs(x['rel']-0.1)<0.03: conf='medium'
    elif i in kpp:
        x=kpp[i]; v=x['v']; rule=x['note']
        if i=='q173c3ae6': conf='medium'; amb='alpha=2 exactly: pulled/pushed transition, speed equals 2sqrt(sD) exactly (c=(a+2)/sqrt(2a)=2)'
        if v=='underdetermined': amb='growth term not given'
    elif i in misc:
        x=misc[i]; v=x['v']; rule=x.get('note','')
        if 'rule' in x:
            rule='Cov(g,m)/(p(1-p)) = -c + r b + d (r+(1-r)p); rule value %s, exact %s'%(x['rule'],x.get('exact','range lo=%s hi=%s'%(x.get('lo'),x.get('hi'))))
            if x['p']=='None' and x['d']!='0': amb='allele frequency not stated while interaction term d!=0; exact sign depends on p (p in (0,1))'
        if v=='underdetermined' and 'C missing' in rule: amb='cost C not stated'
    elif i in wave:
        x=wave[i]; v=x['v']; rule='fastest-growing (max Re lambda) admissible mode n=%s; rel diff %s'%(x['best'],x['rel'])
        if x['rel'] is not None and abs(x['rel']-0.1)<0.04: conf='medium'
        if i=='q4f9af15e': conf='medium'; amb='verdict flips if "fastest-growing" is read as most negative det(J-qD) (mode 39, rel 0.205 => out_of_scope) instead of max Re eigenvalue (mode 32, rel 0.031 => applies); I used max Re lambda'
    elif i in col:
        x=col[i]; v=x['v']; rule='kappa=16 rho g H^3/(E D^2) vs formula 7.829 and exact eigenvalue (taper r=%s)'%x['r']
        if x.get('note')=='no density':
            if x['r']==1.0:
                conf='medium'; amb='density not listed; uniform formula (coefficient 0.788) vs exact Greenhill 0.78773 differ by 3.6e-4 in H, so a thin density band exists in which they disagree (strictly density can matter); I treated uniform formula as equal to exact => settled'
                rule='uniform: formula = exact Greenhill, independent of rho (up to rounding)'
            else:
                rule='tapered exact threshold differs from base-diameter formula by factor ~1.155; density unknown can put column between thresholds'
    out.append(dict(id=i,verdict=v,confidence=conf,rule=rule,ambiguity=amb))
with open('blind_verdicts.jsonl','w') as f:
    for o in out: f.write(json.dumps(o)+'\n')
import collections
print(collections.Counter(o['verdict'] for o in out), len(out))
for o in out:
    if o['ambiguity']!='none' or o['confidence']!='high': print(o['id'],o['verdict'],o['confidence'],o['ambiguity'][:90])
