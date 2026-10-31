import json,re
from fractions import Fraction as F
def load():
    return [json.loads(l) for l in open('blind_input.jsonl')]
NUM=r'-?\d+(?:/\d+)?'
def fr(s):
    s=s.replace(' ','')
    return F(s)
