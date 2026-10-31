"""Critic's manual decidability triage of the 92 Delphi claims that carry LaTeX math.
SOURCE-ONLY JUDGMENT by one reader (the critic), not a validated classification. No second labeller.

Tiers (primary tier only):
  D1  stated proposition is decidable from the displayed math plus at most trivially declared premises
      (exact arithmetic / symbolic algebra / limit / finite enumeration / force balance) - a checker could
      adjudicate it without importing a model that the claim does not state.
  D2  decidable only after hand-authoring a model, definition or theorem the claim does not state
      (derivation under assumptions; PDE/ESS/variational/Laplace-law). The checker then verifies the
      authored formalization, NOT that it is faithful to the claim (fidelity gap).
  E   an empirical measurement or fitted-value claim; adjudicated only by data, never by a prover.
  P   prose / definition / heuristic with no decidable proposition as written.
Index = position in the mathOnly search result saved in delphi_math_claims_raw.json.
"""
import json, sys, collections
LABELS = {
 0:"D2",1:"D2",2:"D2",3:"D2",4:"D1",5:"D2",6:"D2",7:"D2",8:"D1",9:"D1",10:"D2",11:"E",12:"D1",13:"D2",14:"D1",
 15:"D2",16:"D1",17:"D2",18:"P",19:"E",20:"D1",21:"P",22:"D1",23:"D1",24:"E",25:"P",26:"P",27:"D1",28:"E",29:"E",
 30:"P",31:"E",32:"D2",33:"D1",34:"D2",35:"D2",36:"P",37:"D2",38:"P",39:"D1",40:"D1",41:"D2",42:"D1",43:"D2",
 44:"P",45:"D2",46:"D2",47:"D2",48:"D2",49:"D1",50:"P",51:"D1",52:"D1",53:"D1",54:"D2",55:"P",56:"D1",57:"D1",
 58:"D1",59:"D1",60:"P",61:"D1",62:"E",63:"D1",64:"P",65:"D1",66:"D1",67:"D1",68:"D1",69:"E",70:"P",71:"D1",
 72:"D1",73:"D2",74:"P",75:"D1",76:"D2",77:"D2",78:"D2",79:"E",80:"D2",81:"D2",82:"E",83:"D2",84:"P",85:"P",
 86:"E",87:"P",88:"E",89:"D1",90:"P",91:"D1"}
# D1 claims where the checkable content is a bare definition / one-line algebra (no scope question can arise)
TRIVIAL_D1 = {20,22,23,27,56,59,66,12,16,72,75,63,58,57,67,68,71,53}
# claims where the critic can name a specific, non-trivial scope/regime question
SCOPE_INTERESTING = {89:"finite-domain admissible modes (turing_scope, already done)",
 91:"near-onset / large-domain gate of wavelength",
 34:"Rayleigh-Plateau: instability only above a length threshold; finite-length / boundary effects",
 19:"Greenhill buckling is a LIMIT (upper envelope), not a central-tendency slope; operationalisation drift",
 8:"diffusion approximation: valid only for small s and N_e large; neutral limit vs strong selection",
 9:"limit p->0 vs finite p",
 0:"FTNS partial-change form vs total change under epistasis (Delphi record already notes)",
 6:"Hamilton's rule: only for regression-defined r,b,c; fails as a causal rule under non-additivity",
 11:"dN/dS empirical test",
 24:"equal exponent across swimming/flight/walking (empirical)",
 }
def main(raw, out):
    t = json.loads(json.load(open(raw))["search"]["result"]["content"][0]["text"])
    assert len(t) == 92 and set(LABELS) == set(range(92))
    dom = lambda c: c["domain"].rstrip("/").split("/")[-1][:20]
    rows = []
    for i, c in enumerate(t):
        rows.append({"i": i, "id": c["claim"].split("/")[-1], "domain": dom(c), "tier": LABELS[i],
                     "trivial_d1": i in TRIVIAL_D1, "scope_note": SCOPE_INTERESTING.get(i)})
    cnt = collections.Counter(r["tier"] for r in rows)
    bydom = collections.defaultdict(collections.Counter)
    for r in rows: bydom[r["domain"]][r["tier"]] += 1
    summary = {"n": len(rows), "tiers": dict(cnt), "by_domain": {k: dict(v) for k, v in bydom.items()},
               "d1_trivial": sum(1 for r in rows if r["tier"]=="D1" and r["trivial_d1"]),
               "d1_nontrivial": sum(1 for r in rows if r["tier"]=="D1" and not r["trivial_d1"]),
               "judgment": "single-reader manual triage; source-only until an independent second labeller agrees"}
    json.dump({"summary": summary, "rows": rows}, open(out, "w"), indent=1)
    print(json.dumps(summary, indent=1))
if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
