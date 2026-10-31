import DarwinBridge.Checker
import DarwinBridge.Distinction
import DarwinBridge.Certs.CoreKappa2AdmCutHtgrGtvn
import DarwinBridge.Certs.TrpbBlockedDelta005
import DarwinBridge.Certs.TrpbBlockedMultiDelta005
import DarwinBridge.Certs.TrpbRouteDelta0
import DarwinBridge.Certs.TrpbRouteDelta005

-- axiom audit (parsed by scripts/check_proofs.py)
#print axioms DarwinBridge.route_sound
#print axioms DarwinBridge.route_endpoints
#print axioms DarwinBridge.route_floor
#print axioms DarwinBridge.closed_no_reach
#print axioms DarwinBridge.blocked_cut_sound
#print axioms DarwinBridge.adm_cut_sound
#print axioms DarwinBridge.admReach_nd
#print axioms DarwinBridge.routeB_admReach
#print axioms DarwinBridge.contains_satisfiable
#print axioms DarwinBridge.nbrs_complete
#print axioms DarwinBridge.nbrs_sound
#print axioms DarwinBridge.nbrs_length
#print axioms DarwinBridge.adjB_sound
#print axioms DarwinBridge.routeCert_sound
#print axioms DarwinBridge.blockedCert_sound
#print axioms DarwinBridge.admCert_sound
#print axioms DarwinBridge.sensitivity_satisfiable
#print axioms DarwinBridge.route_blocked_exclusive
#print axioms DarwinBridge.route_adm_exclusive
#print axioms DarwinBridge.Distinction.adm_accepts
#print axioms DarwinBridge.Distinction.blocked_rejects
#print axioms DarwinBridge.Distinction.true_route_exists_despite_adm_cut
#print axioms DarwinBridge.Certs.CoreKappa2AdmCutHtgrGtvn.cert_ok
#print axioms DarwinBridge.Certs.CoreKappa2AdmCutHtgrGtvn.instance_sound
#print axioms DarwinBridge.Certs.TrpbBlockedDelta005.cert_ok
#print axioms DarwinBridge.Certs.TrpbBlockedDelta005.instance_sound
#print axioms DarwinBridge.Certs.TrpbBlockedMultiDelta005.cert_ok
#print axioms DarwinBridge.Certs.TrpbBlockedMultiDelta005.instance_sound
#print axioms DarwinBridge.Certs.TrpbRouteDelta0.cert_ok
#print axioms DarwinBridge.Certs.TrpbRouteDelta0.instance_sound
#print axioms DarwinBridge.Certs.TrpbRouteDelta005.cert_ok
#print axioms DarwinBridge.Certs.TrpbRouteDelta005.instance_sound
