import json, collections
from audit_common import *
allr=[]
for p in ('turing','kimura','rest'): allr+=json.load(open(D+f'audit_part_{p}.json'))
over={'gh-0004':('low',),'gh-0012':('low',),'gh-0016':('medium',),'hm-0008':('medium',),'ts-0008':('medium',),'ts-0018':('medium',)}
for r in allr:
    if r['id'] in over: r['confidence']=over[r['id']][0]
allr.sort(key=lambda r:r['id'])
ids=[json.loads(l)['id'] for l in open(D+'audit_input.jsonl')]
assert sorted(ids)==[r['id'] for r in allr] and len(allr)==136
with open(D+'audit_verdicts.jsonl','w') as f:
    for r in allr: f.write(json.dumps({k:r[k] for k in('id','family','verdict','confidence','rule')})+'\n')
c=collections.defaultdict(collections.Counter)
for r in allr: c[r['family']][r['verdict']]+=1
for k,v in c.items(): print(k,dict(v))
print([ (r['id'],r['confidence']) for r in allr if r['confidence']!='high'])
