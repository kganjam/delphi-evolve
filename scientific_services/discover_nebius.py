"""Discover Nebius Scientific AI MCP tools/schemas -> artifacts/services/nebius/."""
import json, sys
from pathlib import Path
from .common import write_json, now_utc, now_seattle
from .nebius_mcp import NebiusMCP

OUT = Path("artifacts/services/nebius")

def main():
    c = NebiusMCP()
    init = c.initialize()
    tools = c.list_tools()
    write_json(OUT / "initialize.json", {"t_utc": now_utc(), "t_seattle": now_seattle(), "result": init})
    write_json(OUT / "tools_list.json", {"t_utc": now_utc(), "n_tools": len(tools), "tools": tools})
    print(len(tools), "tools;", "server:", json.dumps((init or {}).get("serverInfo")))
    for t in tools:
        print(t["name"])

if __name__ == "__main__":
    main()
