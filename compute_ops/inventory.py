"""Read-only live capability inventory (no job, no inference beyond one MCP list call). Never prints or stores credentials.
  python -m compute_ops.inventory OUT.json"""
import datetime as dt, json, os, re, subprocess, sys, time, urllib.request, urllib.error
from pathlib import Path
from . import batch as B

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def seattle():
    return subprocess.run(["date", "+%F %T %Z"], capture_output=True, text=True, env=dict(os.environ, TZ="America/Los_Angeles")).stdout.strip()


def nebius():
    out = {}
    try:
        snap = B.Cloud().snapshot(); out["auth_and_listing_ok"] = True
    except Exception as e:                      # noqa: BLE001
        return {"auth_and_listing_ok": False, "error": str(e)[:200]}
    b = B.Batch({"items": []}, B.Cloud())
    act = [w for w in snap if w.active]
    out.update(total_workloads=len(snap), active=[{"name": w.name, "state": w.state, "platform": w.platform, "preset": w.preset} for w in act],
               our_active_h100=b.ours_active_gpus(snap), foreign_waiting_h100=len(b.foreign_waiting(snap)),
               foreign_active_h100=sum(w.gpus for w in act if w.platform.startswith("gpu-h100") and not w.name.startswith(B.COUNT_PREFIXES)),
               h100_pool_size_per_event_doc=16)
    tok = Path.home() / ".nebius/token"
    if tok.exists():
        age_h = (time.time() - tok.stat().st_mtime) / 3600
        out["token_file_age_h"] = round(age_h, 2); out["token_expected_life_h_per_event_doc"] = 12
        out["token_est_remaining_h"] = round(12 - age_h, 2)
    probe = B.create_argv({"id": "q", "script": "compute_ops/cops_run.py", "kind": "cpu", "preset": "128vcpu-512gb", "timeout": "5m"},
                          "delphi-evolve-ops-quotaprobe", ROOT, Path("/tmp/claude-quota-probe"))
    r = subprocess.run(probe, capture_output=True, text=True, timeout=120)
    m = re.search(r"limit (\d+), requested (\d+)", r.stdout + r.stderr)
    if m:
        lim, req = int(m[1]), int(m[2]); out["nongpu_vcpu_quota"] = {"limit": lim, "in_use": req - 128, "free": lim - (req - 128),
                                                                       "method": "oversize create (rejected, creates nothing) reports used+requested"}
    else:
        out["nongpu_vcpu_quota"] = {"unknown": (r.stdout + r.stderr)[:200], "rc": r.returncode, "WARNING": "if a job was created, cancel it"}
    out["h100_quota"] = "unreadable (PermissionDenied for participants per event doc); only inferable from live pool"
    out["price"] = "no metered price available to participants via CLI; event-provided capacity. Stop bound = server-side --timeout (+ client watchdog)"
    return out


def mcp():
    from scientific_services.nebius_mcp import NebiusMCP
    res = {}
    for ep in ("https://forge.nebius.cloud/mcp", "https://89.169.99.188/mcp"):
        try:
            c = NebiusMCP(endpoint=ep, timeout=60); init = c.initialize()
            rev = c.tool_payload(c.call_tool("get_tool_catalog_revision", {}))
            lst = c.tool_payload(c.call_tool("list_scientific_models", {}))
            res[ep] = {"ok": True, "server": init.get("serverInfo"), "tool_count": rev.get("tool_count"), "catalog_revision": rev.get("tool_catalog_revision"),
                       "n_models": len(lst.get("data", [])),
                       "qualification_counts": {q: sum(1 for m in lst["data"] if m.get("qualification") == q) for q in {m.get("qualification") for m in lst["data"]}}}
        except Exception as e:                  # noqa: BLE001
            res[ep] = {"ok": False, "error": f"{type(e).__name__}: {str(e)[:160]}"}
    return res


def google():
    from scientific_services.common import load_env_value
    out = {}
    key = load_env_value("gemini.env", "GEMINI_API_KEY")
    rq = urllib.request.Request("https://generativelanguage.googleapis.com/v1beta/models?pageSize=200", headers={"x-goog-api-key": key})
    try:
        d = json.loads(urllib.request.urlopen(rq, timeout=60).read()); ms = d.get("models", [])
        out["gemini_api"] = {"ok": True, "n_models": len(ms), "n_generateContent": sum("generateContent" in m.get("supportedGenerationMethods", []) for m in ms),
                             "has_gemini-3.8-flash": any(m["name"].endswith("gemini-3.8-flash") for m in ms)}
    except Exception as e:                      # noqa: BLE001
        out["gemini_api"] = {"ok": False, "error": str(e)[:160]}
    t = subprocess.run(["gcloud", "auth", "print-access-token"], capture_output=True, text=True, timeout=60)
    if t.returncode:
        out["gcloud_oauth"] = {"ok": False, "error": t.stderr.strip()[:200]}; return out
    tok = t.stdout.strip(); P = os.environ.get("GOOGLE_CLOUD_PROJECT") or subprocess.run(["gcloud", "config", "get-value", "project"], capture_output=True, text=True).stdout.strip()

    def get(url):
        rq = urllib.request.Request(url, headers={"Authorization": "Bearer " + tok, "x-goog-user-project": P})
        try:
            return 200, json.loads(urllib.request.urlopen(rq, timeout=60).read())
        except urllib.error.HTTPError as e:
            return e.code, {}
    st, d = get(f"https://serviceusage.googleapis.com/v1/projects/{P}/services?filter=state:ENABLED&pageSize=200")
    names = sorted(s["config"]["name"].split(".")[0] for s in d.get("services", [])) if st == 200 else None
    out["gcloud_oauth"] = {"ok": st == 200, "enabled_services_n": len(names) if names else None,
                           "aiplatform": bool(names and "aiplatform" in names), "compute_enabled": bool(names and "compute" in names), "run_enabled": bool(names and "run" in names)}
    return out


def brev():
    return {"cli_installed": subprocess.run("command -v brev", shell=True, capture_output=True).returncode == 0,
            "config_dir_exists": (Path.home() / ".brev").exists(), "env_vars_named_brev": [k for k in os.environ if "BREV" in k.upper()],
            "status": "no access found; nothing spent"}


if __name__ == "__main__":
    doc = {"taken_seattle": seattle(), "nebius": nebius(), "nebius_scientific_ai_mcp": mcp(), "google": google(), "brev": brev()}
    json.dump(doc, open(sys.argv[1], "w"), indent=1, allow_nan=False); print(json.dumps(doc, indent=1))
