"""Bounded, local MCP and browser checks for the reviewed Frontier pilot."""
import asyncio
from datetime import datetime
import functools
import hashlib
import http.server
import importlib.metadata
import json
from pathlib import Path
import socketserver
import sys
import threading
from zoneinfo import ZoneInfo

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts/integration/codex-api/frontier-interfaces"


def unpack(result):
    assert not result.isError, result
    if result.structuredContent is not None:
        return result.structuredContent
    return json.loads(result.content[0].text)


async def check_mcp():
    params = StdioServerParameters(command=sys.executable,
                                  args=[str(ROOT / "experiments/frontier_mcp/server.py")])
    checks = []
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            assert {t.name for t in tools.tools} == {"frontier_search", "frontier_get_claim", "frontier_contribution_contract", "frontier_prepare_contribution", "frontier_prepare_resource_offer", "frontier_list_problems", "frontier_get_problem", "frontier_prepare_interest"}
            assert all(t.annotations.readOnlyHint for t in tools.tools)
            checks.append("MCP initializes and lists eight read-only tools")
            result = unpack(await session.call_tool("frontier_search", {"query": "", "category": "unchecked", "limit": 7}))
            assert result["total"] == 12 and len(result["results"]) == 7 and result["next_offset"] == 7
            later = unpack(await session.call_tool("frontier_search", {"query": "", "category": "unchecked", "limit": 7, "offset": 7}))
            assert len(later["results"]) == 5 and later["next_offset"] is None
            assert not ({r["id"] for r in result["results"]} & {r["id"] for r in later["results"]})
            checks.append("Review-state filter and pagination preserve twelve unchecked records without overlap")
            empty = unpack(await session.call_tool("frontier_search", {"query": "unfindableterm314159"}))
            assert empty["total"] == 0
            fisher = unpack(await session.call_tool("frontier_get_claim", {"claim_id": "fisher-ftns"}))["claim"]
            assert fisher["category"] == "related" and "not established" in fisher["finding"]
            checks.append("No-hit search stays empty; Fisher remains target-unestablished")
            bad = await session.call_tool("frontier_get_claim", {"claim_id": "fisher-ftns", "expected_version_sha256": "0" * 64})
            assert bad.isError
            unknown = await session.call_tool("frontier_get_claim", {"claim_id": "not-a-claim"})
            assert unknown.isError
            checks.append("Unknown IDs and stale expected versions reject")
            draft = {"claim_id": "fisher-ftns", "claim_version_sha256": fisher["record_sha256"],
                     "author_identifier": "local-protocol-test-unverified", "kind": "scope_review",
                     "statement": "Transport fixture only; not a scientific contribution.",
                     "scope": ["Local interface test"], "limitations": ["Not submitted or scientifically reviewed"],
                     "artifacts": [{"location": "site/review/frontier-data.json",
                                    "sha256": hashlib.sha256((ROOT / "site/review/frontier-data.json").read_bytes()).hexdigest(),
                                    "kind": "source_review"}], "acceptance_requested": "No scientific acceptance requested"}
            good = unpack(await session.call_tool("frontier_prepare_contribution", {"contribution": draft}))
            repeat = unpack(await session.call_tool("frontier_prepare_contribution", {"contribution": draft}))
            assert good == repeat and good["status"] == "draft_unsubmitted" and not good["signed"] and not good["artifact_content_verified"]
            draft["claim_version_sha256"] = "0" * 64
            assert (await session.call_tool("frontier_prepare_contribution", {"contribution": draft})).isError
            checks.append("Draft is deterministic and explicitly unverified/unsubmitted; stale contribution rejects")
            offer = {"provider_identifier": "local-protocol-test-unverified", "resource_kind": "review",
                     "description": "Synthetic protocol fixture; no real resource offered", "capacity": 1,
                     "unit": "test-only unit", "available_until": "2030-01-01T00:00:00Z",
                     "restrictions": ["Not available for execution"], "price_description": "Not an actual price",
                     "verification_method": "None: local transport fixture"}
            offered = unpack(await session.call_tool("frontier_prepare_resource_offer", {"offer": offer}))
            assert not offered["resources_reserved"] and not offered["identity_verified"]
            offer["capacity"] = -1
            assert (await session.call_tool("frontier_prepare_resource_offer", {"offer": offer})).isError
            checks.append("Resource offer remains unreserved and unverified; invalid capacity rejects")
            resource = await session.read_resource("frontier://review-map")
            assert json.loads(resource.contents[0].text) == json.loads((ROOT / "site/review/frontier-data.json").read_text())
            checks.append("MCP resource exactly matches browser map data")
            problems = unpack(await session.call_tool("frontier_list_problems", {"state": "open"}))["problems"]
            assert len(problems) == 6 and all(p["problem"]["state"] == "open" for p in problems)
            completed = unpack(await session.call_tool("frontier_list_problems", {"state": "resolved_in_review"}))["problems"]
            assert len(completed) == 1 and completed[0]["problem"]["id"] == "F007"
            interest = {"problem_id": problems[0]["problem"]["id"], "problem_version_sha256": problems[0]["problem_version_sha256"],
                        "actor_identifier": "local-protocol-test-unverified", "signal": "blocked_by_this", "explanation": "Transport test only"}
            assert (await session.call_tool("frontier_prepare_interest", {"interest": interest})).isError
            interest["signal"] = "following"
            signal = unpack(await session.call_tool("frontier_prepare_interest", {"interest": interest}))
            assert signal["status"] == "draft_unsubmitted" and not signal["registered"]
            assert signal["coordination_url"].startswith("https://github.com/kganjam/delphi-frontier/issues/")
            checks.append("Six open seeds and one resolved correction; interest remains unregistered, blocking signal requires a dependency")
    return {"sdk_version": importlib.metadata.version("mcp"), "checks": checks,
            "limits": "Local SDK client only; synthetic envelopes are test fixtures, not submitted evidence or actual resource offers. No observed external reuse."}


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def check_browser():
    server = socketserver.TCPServer(("127.0.0.1", 0), functools.partial(QuietHandler, directory=str(ROOT / "site")))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    data = json.loads((ROOT / "site/review/frontier-data.json").read_text())
    receipts = {}
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(args=["--no-sandbox", "--renderer-process-limit=2"])
            for name, size in {"desktop": (1440, 1080), "mobile": (390, 844)}.items():
                page = browser.new_page(viewport={"width": size[0], "height": size[1]})
                errors = []
                page.on("pageerror", lambda e: errors.append(str(e)))
                page.on("requestfailed", lambda r: errors.append(r.url))
                page.on("response", lambda r: errors.append(f"HTTP {r.status}: {r.url}") if r.status >= 400 else None)
                page.goto(base + "/review/frontier.html", wait_until="networkidle")
                assert page.locator(".node").count() == 21
                assert page.locator(".problem-card").count() == 7
                assert page.locator(".join-link").count() == 6
                for node in data["nodes"]:
                    page.select_option("#claim-picker", node["id"])
                    assert page.locator("#claim-panel").get_attribute("data-claim-id") == node["id"]
                    page.click("#prove-button")
                    assert page.locator("#evidence-panel").is_visible()
                    assert page.locator("#claim-hash").text_content() == node["record_sha256"]
                    assert page.locator("#claim-finding").text_content() == node["finding"]
                page.locator('.node[data-id="fisher-ftns"]').focus()
                page.keyboard.press("Enter")
                assert page.locator("#claim-panel").get_attribute("data-claim-id") == "fisher-ftns"
                assert "target unestablished" in page.locator("#claim-status").inner_text()
                page.select_option("#claim-picker", "turing-ddi")
                page.click("#prove-button")
                assert page.locator('#evidence-links a[href$="/review/index.html"]').count() == 1
                overflow = page.evaluate("Math.max(0, document.documentElement.scrollWidth - innerWidth)")
                assert overflow == 0, (name, overflow)
                page.evaluate("window.scrollTo(0,0)")
                page.screenshot(path=str(OUT / f"{name}.png"), full_page=True)
                assert not errors, errors
                receipts[name] = {"viewport": size, "claims_inspected": 21, "seed_cards": 7, "coordination_links": 6, "keyboard_selection": "passed",
                                  "horizontal_overflow_px": overflow, "errors": errors,
                                  "screenshot": f"{name}.png"}
                page.close()
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
    return receipts


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    mcp = asyncio.run(asyncio.wait_for(check_mcp(), timeout=45))
    browser = check_browser()
    paths = list((ROOT / "site/review").glob("frontier*")) + [ROOT / "experiments/frontier_mcp/server.py"]
    receipt = {"recorded_at": datetime.now(ZoneInfo("America/Los_Angeles")).isoformat(),
               "mcp": mcp, "browser": browser,
               "source_hashes": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}}
    (OUT / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"mcp_checks": len(mcp["checks"]), "browser_viewports": list(browser), "receipt": str(OUT / "receipt.json")}))


if __name__ == "__main__":
    main()
