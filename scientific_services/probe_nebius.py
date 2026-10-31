"""Read-only probes: list_scientific_models, get_model_schema for given model ids."""
import json, sys
from pathlib import Path
from .common import write_json, now_utc
from .nebius_mcp import NebiusMCP
OUT = Path("artifacts/services/nebius")

def main(models):
    c = NebiusMCP(); c.initialize()
    rev = c.tool_payload(c.call_tool("get_tool_catalog_revision", {}))
    lst = c.tool_payload(c.call_tool("list_scientific_models", {}))
    write_json(OUT / "catalog_revision.json", {"t_utc": now_utc(), "payload": rev})
    write_json(OUT / "scientific_models.json", {"t_utc": now_utc(), "payload": lst})
    for m in models:
        sch = c.tool_payload(c.call_tool("get_model_schema", {"model_id": m}))
        write_json(OUT / f"schema_{m}.json", {"t_utc": now_utc(), "model_id": m, "payload": sch})
        print(m, "->", len(json.dumps(sch)), "bytes")

if __name__ == "__main__":
    main(sys.argv[1:])
