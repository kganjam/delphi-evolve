"""Uniform model adapter: one `complete()` call for six model families, with per-call token
accounting, served-model verification and account attribution.

Design rules (each learned from a probe, see tasks/results/guilds.json):
  * Orchestra's `acquire_credentials(preferred="glm"|"minimax"|"gemini"|"max_allen")` does NOT
    honour the name: it returns whichever Claude Max account has headroom. We therefore record
    `creds.provider` (the account actually served), and GLM/MiniMax go through the key pool, not
    the OAuth allocator. A label is never trusted: `served_model` is read from the provider
    response and `family_verified` is False unless it matches the family.
  * Credentials live only in a child-process env dict in memory. Nothing is printed or logged;
    stderr is truncated and scrubbed before it is stored.
  * Every call: no tools, empty scratch cwd, isolated config home (so no user CLAUDE.md / AGENTS.md /
    memories reach the model), isolation scan of the exact text sent, token-ledger pre-check + record.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
import uuid
from abc import ABC, abstractmethod
from contextlib import contextmanager
from dataclasses import dataclass, field, asdict
from pathlib import Path

from .accounting import TokenLedger, Usage, now_stamps
import hashlib


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def assert_clean(forbidden: "list[str]", *texts: str) -> None:
    """Arm isolation guard: refuse to send text containing any forbidden marker (e.g. ids of commons
    entries that the no-commons arm must never see)."""
    blob = "\n".join(texts)
    for f in forbidden:
        if f and f in blob:
            raise AdapterError("isolation violation: prompt contains a forbidden marker")

FAMILY_MODEL_PATTERNS = {
    "claude": re.compile(r"^claude-", re.I),
    "gpt": re.compile(r"^(gpt|o\d|codex)", re.I),
    "gemini": re.compile(r"^(models/)?gemini", re.I),
    "glm": re.compile(r"^glm", re.I),
    "grok": re.compile(r"^grok", re.I),
    "minimax": re.compile(r"minimax", re.I),
}
_TOKENISH = re.compile(r"[A-Za-z0-9_\-\.]{32,}")


def scrub(text: str, limit: int = 400) -> str:
    return _TOKENISH.sub("<redacted>", text or "")[:limit]


class AdapterError(RuntimeError):
    pass


@dataclass
class CallResult:
    call_id: str
    family: str
    harness: str
    account: str
    requested_model: str
    served_model: str
    served_model_source: str       # provider_response | rollout_file | requested_only
    family_verified: bool
    text: str
    usage: Usage
    latency_s: float
    cost_basis: str                # subscription | api_key_pool | free_tier | metered
    cli_list_price_usd: float | None   # informational list-price estimate; NOT actual spend
    system_sha256: str
    prompt_sha256: str
    ok: bool
    error: str = ""
    extra: dict = field(default_factory=dict)

    def to_record(self) -> dict:
        d = asdict(self)
        d.pop("text")           # text is stored by the forecast store, not the token ledger
        d.pop("usage")
        d["response_sha256"] = sha256_text(self.text)
        return d


class ModelAdapter(ABC):
    family: str
    harness: str
    default_model: str

    def __init__(self, model: str | None = None, *, timeout_s: int = 240):
        self.model = model or self.default_model
        self.timeout_s = timeout_s

    # Subclasses implement the raw call. Everything else is common.
    @abstractmethod
    def _call(self, system: str, user: str, max_output_tokens: int) -> CallResult: ...

    def complete(self, system: str, user: str, *, tag: str, ledger: TokenLedger, budget_key: str,
                 max_output_tokens: int = 1200, reserve_tokens: int | None = None,
                 forbidden: "list[str] | None" = None) -> CallResult:
        assert_clean(forbidden or [], system, user)       # fail closed on the exact bytes sent
        ledger.check(budget_key, reserve_tokens if reserve_tokens is not None else 0)
        t0 = time.time()
        try:
            res = self._call(system, user, max_output_tokens)
        except Exception as e:  # noqa: BLE001
            res = CallResult(call_id=str(uuid.uuid4()), family=self.family, harness=self.harness, account="unknown",
                             requested_model=self.model, served_model="", served_model_source="requested_only",
                             family_verified=False, text="", usage=Usage(source="estimated"),
                             latency_s=time.time() - t0, cost_basis="unknown", cli_list_price_usd=None,
                             system_sha256=sha256_text(system), prompt_sha256=sha256_text(user), ok=False,
                             error=scrub(f"{type(e).__name__}: {e}"))
        res.system_sha256 = sha256_text(system)
        res.prompt_sha256 = sha256_text(user)
        rec = res.to_record()
        rec["tag"] = tag
        ledger.record(budget_key, rec, res.usage)
        return res

    @staticmethod
    def _verify(family: str, served: str) -> bool:
        return bool(served) and bool(FAMILY_MODEL_PATTERNS[family].search(served))


def _run(cmd: list[str], *, stdin: str | None, env: dict, cwd: str, timeout: int) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, input=stdin, text=True, capture_output=True, cwd=cwd, env=env, timeout=timeout)


def _base_env() -> dict:
    env = os.environ.copy()
    for k in list(env):
        if (k.startswith("ANTHROPIC_") or k.startswith("CLAUDE_") or k.startswith("OPENAI_")
                or k in {"GLM_API_KEY", "ZHIPUAI_API_KEY", "MINIMAX_API_KEY", "MINIMAX_API_KEY_2", "GEMINI_API_KEY",
                         "XAI_API_KEY", "CODEX_HOME", "GROK_HOME"}):
            env.pop(k, None)
    env["OMP_NUM_THREADS"] = env["OPENBLAS_NUM_THREADS"] = "1"
    return env


@contextmanager
def oauth_lease(preferred: str, requested_model: str = ""):
    """Managed Orchestra subscription allocation. Yields (account_name, env_vars). Releases on exit."""
    from orchestra.auth import acquire_credentials, release_credentials
    wid = "delphi-guilds-" + str(uuid.uuid4())
    creds = acquire_credentials(worker_id=wid, preferred=preferred, requested_model=requested_model)
    if creds is None:
        raise AdapterError(f"no managed allocation available for {preferred!r}")
    try:
        yield creds.provider, dict(creds.env_vars)
    finally:
        release_credentials(worker_id=wid)


@contextmanager
def key_lease(pool: str, accounts: tuple[str, ...] = ()):
    """Managed Orchestra key-pool credential for an API-key account (GLM / MiniMax), resolved in memory.
    `acquire_key` only reads the process env, which does not carry these keys here, so we use
    `key_env_for_account` (host-env fallback). It does not register a concurrency slot; callers
    bound concurrency themselves. Yields (account_name, env_vars); tries accounts in order."""
    from orchestra import key_pool
    last = ""
    for acct in accounts or (pool,):
        prov, env_vars, err = key_pool.key_env_for_account(acct)
        if env_vars:
            yield acct, dict(env_vars)
            return
        last = err
    raise AdapterError(f"no usable key for pool {pool!r}: {last}")


class ClaudeCLIAdapter(ModelAdapter):
    served_source = "provider_response"
    """Claude Sonnet via the `claude` CLI on a Max subscription (never an API-key route)."""
    family = "claude"
    harness = "claude-cli"
    default_model = "sonnet"
    CLAUDE_BIN = "/home/ubuntu/.local/bin/claude"

    def _cli_args(self, system: str, max_output_tokens: int) -> list[str]:
        return [self.CLAUDE_BIN, "-p", "--model", self.model, "--tools", "", "--no-session-persistence",
                "--setting-sources", "", "--disable-slash-commands", "--strict-mcp-config",
                "--system-prompt", system, "--output-format", "json"]

    def _lease(self):
        return oauth_lease("claude", "sonnet")

    def _env_for(self, account: str, env_vars: dict, scratch: str) -> tuple[dict, str]:
        if not (account.startswith("max_") or account.startswith("ent_")):
            raise AdapterError(f"allocation {account!r} is not a Max/Enterprise subscription; refusing")
        env = _base_env()
        env.update(env_vars)
        return env, "subscription"

    def _call(self, system: str, user: str, max_output_tokens: int) -> CallResult:
        t0 = time.time()
        with self._lease() as (account, env_vars), tempfile.TemporaryDirectory(prefix="guild-") as scratch:
            env, basis = self._env_for(account, env_vars, scratch)
            r = _run(self._cli_args(system, max_output_tokens), stdin=user, env=env, cwd=scratch, timeout=self.timeout_s)
            leftovers = os.listdir(scratch)
        try:
            j = json.loads(r.stdout)
        except Exception:
            raise AdapterError(f"unparseable CLI output rc={r.returncode}: {scrub(r.stdout or r.stderr)}")
        mu = j.get("modelUsage") or {}
        served = ",".join(sorted(mu)) or ""
        u = Usage()
        for m in mu.values():
            u.input_tokens += int(m.get("inputTokens", 0))
            u.output_tokens += int(m.get("outputTokens", 0))
            u.cache_read_tokens += int(m.get("cacheReadInputTokens", 0))
            u.cache_creation_tokens += int(m.get("cacheCreationInputTokens", 0))
            u.reasoning_tokens += int(m.get("thinkingTokens", 0) or 0)
        if not mu:
            us = j.get("usage") or {}
            u = Usage(int(us.get("input_tokens", 0)), int(us.get("output_tokens", 0)),
                      int(us.get("cache_read_input_tokens", 0)), int(us.get("cache_creation_input_tokens", 0)))
        ok = (not j.get("is_error")) and r.returncode == 0 and bool(j.get("result"))
        verified = bool(mu) and all(self._verify(self.family, m) for m in mu)
        return CallResult(call_id=str(uuid.uuid4()), family=self.family, harness=self.harness, account=account,
                          requested_model=self.model, served_model=served, served_model_source=self.served_source,
                          family_verified=verified, text=j.get("result") or "", usage=u, latency_s=time.time() - t0,
                          cost_basis=basis, cli_list_price_usd=j.get("total_cost_usd"),
                          system_sha256="", prompt_sha256="", ok=ok,
                          error="" if ok else scrub(str(j.get("result") or r.stderr)),
                          extra={"scratch_leftovers": leftovers, "stop_reason": j.get("stop_reason")})


class _ClaudeCompatAdapter(ClaudeCLIAdapter):
    """Anthropic-protocol third-party endpoint driven through the same CLI (GLM, MiniMax)."""
    served_source = "cli_echo_of_configured_model"   # the CLI reports the model name it was told to use; the endpoint host is the only other evidence
    pool: str
    base_url: str
    token_env: str

    accounts: tuple = ()

    def _lease(self):
        return key_lease(self.pool, self.accounts)

    def _env_for(self, account, env_vars, scratch):
        key = env_vars.get(self.token_env, "")
        if not key:
            raise AdapterError(f"{self.pool} key not configured in managed pool")
        env = _base_env()
        env.update({"ANTHROPIC_BASE_URL": os.environ.get(self.pool.upper() + "_ANTHROPIC_BASE_URL", self.base_url),
                    "ANTHROPIC_AUTH_TOKEN": key, "ANTHROPIC_MODEL": self.model,
                    "ANTHROPIC_SMALL_FAST_MODEL": self.model,
                    "CLAUDE_CONFIG_DIR": scratch + "/.cfg", "CLAUDE_AUTH_PROVIDER": self.pool,
                    "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1"})
        return env, "api_key_pool"


class GLMAdapter(_ClaudeCompatAdapter):
    family, harness, default_model = "glm", "claude-cli@z.ai", "glm-4.5"
    pool, base_url, token_env = "glm", "https://api.z.ai/api/anthropic", "GLM_API_KEY"
    accounts = ("glm_kg",)


class MiniMaxAdapter(_ClaudeCompatAdapter):
    family, harness, default_model = "minimax", "claude-cli@minimax", "MiniMax-M3.1-Flash"
    pool, base_url, token_env = "minimax", "https://api.minimax.io/anthropic", "MINIMAX_API_KEY"
    accounts = ("minimax_kg", "minimax_kg1")


class CodexAdapter(ModelAdapter):
    """GPT via `codex exec` on the managed ChatGPT/Codex subscription, with an isolated CODEX_HOME
    (symlinked auth only) so ~/.codex/AGENTS.md and memories never reach the model."""
    family = "gpt"
    harness = "codex-cli"
    default_model = "gpt-5.6-sol"
    effort = "low"
    CODEX_BIN = "/usr/bin/codex"

    def _call(self, system: str, user: str, max_output_tokens: int) -> CallResult:
        t0 = time.time()
        with oauth_lease("codex") as (account, env_vars), tempfile.TemporaryDirectory(prefix="guild-") as scratch:
            real_home = env_vars.get("CODEX_HOME") or os.path.expanduser("~/.codex")
            home = Path(scratch) / "codex_home"
            home.mkdir()
            (home / "auth.json").symlink_to(Path(real_home) / "auth.json")   # symlink, not a copy
            (home / "config.toml").write_text(f'model = "{self.model}"\nmodel_reasoning_effort = "{self.effort}"\n')
            work = Path(scratch) / "cwd"
            work.mkdir()
            env = _base_env()
            env["CODEX_HOME"] = str(home)
            prompt = system + "\n\n=====\n\n" + user
            r = _run([self.CODEX_BIN, "exec", "--json", "--skip-git-repo-check", "--ignore-rules",
                      "--sandbox", "read-only", "-m", self.model], stdin=prompt, env=env, cwd=str(work),
                     timeout=self.timeout_s)
            text, usage, thread = "", None, ""
            for line in r.stdout.splitlines():
                try:
                    ev = json.loads(line)
                except Exception:
                    continue
                if ev.get("type") == "thread.started":
                    thread = ev.get("thread_id", "")
                elif ev.get("type") == "item.completed" and (ev.get("item") or {}).get("type") == "agent_message":
                    text = ev["item"].get("text", "")
                elif ev.get("type") == "turn.completed":
                    usage = ev.get("usage")
            served, src = "", "requested_only"
            for f in (home / "sessions").rglob("*.jsonl") if (home / "sessions").exists() else []:
                for line in f.read_text().splitlines():
                    try:
                        o = json.loads(line)
                    except Exception:
                        continue
                    m = (o.get("payload") or {}).get("model") if isinstance(o.get("payload"), dict) else None
                    if m:
                        served, src = m, "rollout_file"
                        break
                if served:
                    break
        if usage is None:
            raise AdapterError(f"codex produced no usage rc={r.returncode}: {scrub(r.stderr)}")
        u = Usage(input_tokens=int(usage.get("input_tokens", 0)) - int(usage.get("cached_input_tokens", 0)),
                  output_tokens=int(usage.get("output_tokens", 0)),
                  cache_read_tokens=int(usage.get("cached_input_tokens", 0)),
                  cache_creation_tokens=int(usage.get("cache_write_input_tokens", 0)),
                  reasoning_tokens=int(usage.get("reasoning_output_tokens", 0)))
        ok = r.returncode == 0 and bool(text)
        return CallResult(call_id=str(uuid.uuid4()), family=self.family, harness=self.harness, account=account,
                          requested_model=self.model, served_model=served or self.model, served_model_source=src,
                          family_verified=(src != "requested_only" and self._verify("gpt", served)),
                          text=text, usage=u, latency_s=time.time() - t0, cost_basis="subscription",
                          cli_list_price_usd=None, system_sha256="", prompt_sha256="", ok=ok,
                          error="" if ok else scrub(r.stderr), extra={"thread_id": thread, "reasoning_effort": self.effort})


class GeminiAdapter(ModelAdapter):
    """Gemini via the Generative Language API with the event's AI Studio key (read into a header only)."""
    family = "gemini"
    harness = "gemini-api"
    default_model = "gemini-3.8-flash"
    BASE = "https://generativelanguage.googleapis.com/v1beta"

    def _key(self) -> str:
        from scientific_services.common import load_env_value
        return load_env_value("gemini.env", "GEMINI_API_KEY")

    def _call(self, system: str, user: str, max_output_tokens: int) -> CallResult:
        t0 = time.time()
        body = {"systemInstruction": {"parts": [{"text": system}]},
                "contents": [{"role": "user", "parts": [{"text": user}]}],
                "generationConfig": {"maxOutputTokens": max_output_tokens, "temperature": 0.0}}
        req = urllib.request.Request(f"{self.BASE}/models/{self.model}:generateContent", data=json.dumps(body).encode(),
                                     method="POST", headers={"x-goog-api-key": self._key(), "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
                j = json.loads(resp.read())
        except urllib.error.HTTPError as e:
            raise AdapterError(f"gemini HTTP {e.code}: {scrub(e.read().decode('utf-8', 'replace'))}")
        um = j.get("usageMetadata") or {}
        cands = j.get("candidates") or [{}]
        text = "".join(p.get("text", "") for p in (cands[0].get("content") or {}).get("parts", []) if not p.get("thought"))
        thoughts = int(um.get("thoughtsTokenCount", 0))
        cached = int(um.get("cachedContentTokenCount", 0))
        u = Usage(input_tokens=int(um.get("promptTokenCount", 0)) - cached,
                  output_tokens=int(um.get("candidatesTokenCount", 0)) + thoughts,
                  cache_read_tokens=cached, reasoning_tokens=thoughts)
        served = j.get("modelVersion", "")
        ok = bool(text)
        return CallResult(call_id=str(uuid.uuid4()), family=self.family, harness=self.harness,
                          account="gemini_event_key", requested_model=self.model, served_model=served,
                          served_model_source="provider_response" if served else "requested_only",
                          family_verified=self._verify("gemini", served), text=text, usage=u,
                          latency_s=time.time() - t0, cost_basis="event_key_unmetered_unverified", cli_list_price_usd=None,
                          system_sha256="", prompt_sha256="", ok=ok, error="" if ok else scrub(json.dumps(j)[:300]),
                          extra={"finish_reason": cands[0].get("finishReason")})


class GrokAdapter(ModelAdapter):
    """Grok via the `grok` CLI on the managed SuperGrok login (GROK_HOME). The only managed Grok
    account was at 100% weekly rate limit until 2026-11-03 03:15 when this was written; the
    adapter therefore reports UNAVAILABLE rather than being exercised (see results JSON)."""
    family = "grok"
    harness = "grok-cli"
    default_model = "grok-4.6"
    GROK_BIN = "/home/ubuntu/.local/bin/grok"

    def _call(self, system: str, user: str, max_output_tokens: int) -> CallResult:
        t0 = time.time()
        with oauth_lease("grok_outlook") as (account, env_vars), tempfile.TemporaryDirectory(prefix="guild-") as scratch:
            env = _base_env()
            home = env_vars.get("GROK_HOME")
            if home:
                env["GROK_HOME"] = home
            pf = Path(scratch) / "prompt.txt"
            pf.write_text(user)
            r = _run([self.GROK_BIN, "--prompt-file", str(pf), "--output-format", "json", "-m", self.model,
                      "--system-prompt-override", system, "--tools", "", "--no-subagents", "--disable-web-search",
                      "--permission-mode", "dontAsk"], stdin=None, env=env, cwd=scratch, timeout=self.timeout_s)
        try:
            j = json.loads(r.stdout)
        except Exception:
            raise AdapterError(f"grok unparseable rc={r.returncode}: {scrub(r.stdout or r.stderr)}")
        us = j.get("usage") or {}
        u = Usage(int(us.get("input_tokens", 0)), int(us.get("output_tokens", 0)),
                  int(us.get("cache_read_input_tokens", 0)), int(us.get("cache_creation_input_tokens", 0)))
        served = j.get("model", "")
        text = j.get("result") or j.get("text") or ""
        return CallResult(call_id=str(uuid.uuid4()), family=self.family, harness=self.harness, account=account,
                          requested_model=self.model, served_model=served,
                          served_model_source="provider_response" if served else "requested_only",
                          family_verified=self._verify("grok", served), text=text, usage=u, latency_s=time.time() - t0,
                          cost_basis="subscription", cli_list_price_usd=None, system_sha256="", prompt_sha256="",
                          ok=bool(text), error="" if text else scrub(r.stderr or r.stdout))


ADAPTERS = {"claude": ClaudeCLIAdapter, "gpt": CodexAdapter, "gemini": GeminiAdapter,
            "glm": GLMAdapter, "grok": GrokAdapter, "minimax": MiniMaxAdapter}


def make_adapter(family: str, model: str | None = None, **kw) -> ModelAdapter:
    if family not in ADAPTERS:
        raise ValueError(f"unknown family {family!r}; choose from {sorted(ADAPTERS)}")
    return ADAPTERS[family](model, **kw)
