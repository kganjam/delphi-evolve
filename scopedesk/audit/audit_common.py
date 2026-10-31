import json, os
from fractions import Fraction as F
D='/tmp/claude-1000/-data-worktrees-delphi-evolve-rethink-director/017a3abe-6332-43df-8ad6-27debd7c7730/scratchpad/audit/'
def load():
    return [json.loads(l) for l in open(D+'audit_input.jsonl')]
def fr(x): return None if x is None else F(x)
def save(fam, out):
    with open(D+f'audit_part_{fam}.json','w') as f: json.dump(out,f,indent=1)
