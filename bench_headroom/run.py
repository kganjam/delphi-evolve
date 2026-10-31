"""Run arm U (unguarded, prompt only) on the frozen bench v1.2 payload for one model family; score separately.
Reads the frozen files via `git show` from the critic's branch (read-only). Fails closed on hash mismatch."""
import hashlib, json, random, subprocess, sys, time
from pathlib import Path

from lean_commons.accounting import TokenLedger
from lean_commons.adapters import make_adapter, sha256_text

REF = "origin/work/rethink-critic"
BASE = "scopedesk/bench/v1_2/"
PAYLOAD_SHA = "6c571db13a63d5dc8e8b5e5fadda601471f9a0a4fad6053f798395a48f78ee42"
KEY_SHA = "28645a12f2f4c77fc1acedb10b23b4070832eefa381b88ca65a12b9e4ecdaa2f"
SYSTEM = ("You answer one scoped-applicability question. Reply with ONLY a JSON object "
          '{"verdict": "applies" | "out_of_scope" | "underdetermined"}. No other text.')
VERDICTS = ("applies", "out_of_scope", "underdetermined")


def show(path: str) -> bytes:
    return subprocess.run(["git", "show", f"{REF}:{BASE}{path}"], capture_output=True, check=True).stdout


def parse(text: str):
    import re
    m = re.search(r"\{.*?\}", text or "", re.S)
    if not m:
        return None
    try:
        v = json.loads(m.group(0)).get("verdict")
    except Exception:
        return None
    return v if v in VERDICTS else None


def run(family: str, out: Path, limit: int | None = None):
    payload = show("model_payload.jsonl")
    assert hashlib.sha256(payload).hexdigest() == PAYLOAD_SHA, "payload hash mismatch (fail closed)"
    items = [json.loads(l) for l in payload.decode().splitlines() if l.strip()]
    random.Random(20261031).shuffle(items)
    if limit:
        items = items[:limit]
    out.mkdir(parents=True, exist_ok=True)
    ad = make_adapter(family)
    led = TokenLedger(out / "ledger.jsonl", {"u": 1_500_000})
    resp = out / "responses.jsonl"
    done = {json.loads(l)["id"] for l in resp.read_text().splitlines()} if resp.exists() else set()
    for it in items:
        if it["id"] in done:
            continue
        r = None
        for k in range(3):
            r = ad.complete(SYSTEM, it["prompt"], tag=it["id"], ledger=led, budget_key="u", max_output_tokens=600, reserve_tokens=6000)
            if r.ok:
                break
            time.sleep(3 * (k + 1))
        row = {"id": it["id"], "family": r.family, "account": r.account, "served_model": r.served_model, "family_verified": r.family_verified,
               "ok": r.ok, "text": r.text, "verdict": parse(r.text), "tokens": r.usage.total, "call_id": r.call_id}
        with resp.open("a") as f:
            f.write(json.dumps(row) + "\n")
    (out / "RUN.json").write_text(json.dumps({"family": family, "system_sha256": sha256_text(SYSTEM), "payload_sha256": PAYLOAD_SHA,
                                              "n": len(items), "tokens": led.spent("u")}, indent=1))


if __name__ == "__main__":
    run(sys.argv[1], Path(sys.argv[2]), int(sys.argv[3]) if len(sys.argv) > 3 else None)
