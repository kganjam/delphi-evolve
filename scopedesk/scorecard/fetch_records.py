"""Fetch the 21 math-domain Delphi claim records (18 population-genetics + 3 Turing) from the hosted keyless MCP, local source, read-only.
Saves the raw tool result per claim to records/<id>.json with the retrieval time and sha256 of the raw text. Usage: python3 -I fetch_records.py"""
import json, hashlib, datetime, urllib.request, os
URL = "https://delphisci-mcp.fly.dev/mcp"; D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "records")
def call(name, args, i):
    body = json.dumps({"jsonrpc": "2.0", "id": i, "method": "tools/call", "params": {"name": name, "arguments": args}}).encode()
    req = urllib.request.Request(URL, body, {"content-type": "application/json", "accept": "application/json, text/event-stream"})
    raw = urllib.request.urlopen(req, timeout=60).read().decode()
    if "\ndata:" in raw or raw.startswith("event:"): raw = [l[5:] for l in raw.splitlines() if l.startswith("data:")][-1]
    return json.loads(raw)
res = call("delphi_search_claims", {"mathOnly": True, "limit": 500, "source": "local"}, 1)
claims = json.loads(res["result"]["content"][0]["text"])
keep = [c for c in claims if c["domain"].endswith("math-population-genetics-and-evolutionary-theory") or "reaction-diffusion" in c["domain"]]
assert len(keep) == 21, len(keep)
for n, c in enumerate(keep):
    cid = c["claim"].rsplit("/", 1)[-1]; r = call("delphi_get_claim", {"id": cid, "source": "local"}, 10 + n); txt = r["result"]["content"][0]["text"]
    json.dump({"claim_id": cid, "retrieved_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "source": "local", "raw_text_sha256": hashlib.sha256(txt.encode()).hexdigest(),
               "search_row": c, "record": json.loads(txt)}, open(os.path.join(D, cid + ".json"), "w"), indent=1)
print(len(keep), "records saved")
