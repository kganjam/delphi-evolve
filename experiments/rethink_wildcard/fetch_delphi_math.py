"""Fetch every Delphi claim carrying LaTeX (skos:notation) from the hosted keyless MCP and save raw JSON.
Read-only queries. Usage: python3 -I fetch_delphi_math.py OUT.json"""
import json, sys, urllib.request, hashlib, datetime
URL = "https://delphisci-mcp.fly.dev/mcp"
def call(name, args, i):
    body = json.dumps({"jsonrpc":"2.0","id":i,"method":"tools/call","params":{"name":name,"arguments":args}}).encode()
    req = urllib.request.Request(URL, body, {"content-type":"application/json","accept":"application/json, text/event-stream"})
    raw = urllib.request.urlopen(req, timeout=60).read().decode()
    if raw.startswith("event:") or "\ndata:" in raw:
        raw = [l[5:] for l in raw.splitlines() if l.startswith("data:")][-1]
    return json.loads(raw), raw
ov, _ = call("delphi_overview", {"source":"local"}, 1)
res, raw = call("delphi_search_claims", {"mathOnly": True, "limit": 500, "source":"local"}, 2)
out = {"queried_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "overview": ov, "search": res,
       "search_raw_sha256": hashlib.sha256(raw.encode()).hexdigest()}
json.dump(out, open(sys.argv[1], "w"), indent=1)
print(json.dumps(ov)[:1500]); print(len(raw))
