"""Simple Gemini API (Generative Language, AI Studio key) client with a persistent budget ledger.

* Key is read from ~/.config/morphoswarm/gemini.env (GEMINI_API_KEY) into the x-goog-api-key header only.
* Every call is recorded (prompt, model id requested + modelVersion returned, response, usageMetadata,
  UTC + Seattle timestamps) after redaction. Responses are MODEL OPINION, not verified truth.
* The ledger enforces the task cap: at most MAX_CALLS calls, MAX_IN input tokens, MAX_OUT output tokens
  (thinking tokens counted as output) across the whole task. Input is pre-checked with countTokens.
* Only public repository/scientific text may be passed; callers are responsible for that, and
  `assert_public_text` refuses text containing known secret values.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from pathlib import Path

from .common import load_env_value, now_seattle, now_utc, redact, sha256_text, _secret_values

BASE = "https://generativelanguage.googleapis.com/v1beta"
LEDGER = Path("artifacts/services/gemini/usage_ledger.json")
MAX_CALLS, MAX_IN, MAX_OUT = 6, 150_000, 30_000


class BudgetExceeded(RuntimeError):
    pass


def _load_ledger():
    if LEDGER.exists():
        return json.loads(LEDGER.read_text())
    return {"caps": {"max_calls": MAX_CALLS, "max_input_tokens": MAX_IN, "max_output_tokens": MAX_OUT},
            "calls": 0, "input_tokens": 0, "output_tokens": 0, "entries": []}


def _save_ledger(l):
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    LEDGER.write_text(json.dumps(redact(l), indent=1) + "\n")


def assert_public_text(text: str):
    for v in _secret_values:
        if v in text:
            raise ValueError("refusing to send text containing a credential value")


class Gemini:
    def __init__(self, timeout=300):
        self._key = load_env_value("gemini.env", "GEMINI_API_KEY")
        self.timeout = timeout

    def _post(self, path, body):
        req = urllib.request.Request(f"{BASE}/{path}", data=json.dumps(body).encode(), method="POST",
                                     headers={"x-goog-api-key": self._key, "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8", "replace")
            try:
                return e.code, json.loads(raw)
            except Exception:
                return e.code, {"raw": raw[:2000]}

    def count_tokens(self, model, text, system=None):
        inner = {"model": f"models/{model}", "contents": [{"parts": [{"text": text}]}]}
        if system:
            inner["systemInstruction"] = {"parts": [{"text": system}]}
        st, js = self._post(f"models/{model}:countTokens", {"generateContentRequest": inner})
        if st != 200:
            raise RuntimeError(f"countTokens HTTP {st}: {json.dumps(redact(js))[:500]}")
        return js["totalTokens"]

    def generate(self, model, prompt, *, system=None, max_output_tokens=8192, temperature=0.2,
                 label="", out_dir=Path("artifacts/services/gemini"), response_mime_type=None, thinking_level=None):
        assert_public_text(prompt + (system or ""))
        led = _load_ledger()
        n_in = self.count_tokens(model, prompt, system)       # countTokens is not a generate call
        if led["calls"] + 1 > MAX_CALLS:
            raise BudgetExceeded("call cap reached")
        if led["input_tokens"] + n_in > MAX_IN:
            raise BudgetExceeded(f"input token cap: {led['input_tokens']}+{n_in} > {MAX_IN}")
        if led["output_tokens"] + max_output_tokens > MAX_OUT:
            raise BudgetExceeded(f"output cap: {led['output_tokens']}+{max_output_tokens} > {MAX_OUT}")
        gen_cfg = {"temperature": temperature, "maxOutputTokens": max_output_tokens}
        if response_mime_type:
            gen_cfg["responseMimeType"] = response_mime_type
        if thinking_level:                      # Gemini 3: "minimal" | "low" | "medium" | "high"
            gen_cfg["thinkingConfig"] = {"thinkingLevel": thinking_level}
        body = {"contents": [{"role": "user", "parts": [{"text": prompt}]}], "generationConfig": gen_cfg}
        if system:
            body["systemInstruction"] = {"parts": [{"text": system}]}
        t0 = time.time(); t_utc, t_sea = now_utc(), now_seattle()
        status, js = self._post(f"models/{model}:generateContent", body)
        elapsed = round(time.time() - t0, 1)
        um = js.get("usageMetadata", {}) if isinstance(js, dict) else {}
        used_in = um.get("promptTokenCount", n_in)
        used_out = (um.get("candidatesTokenCount", 0) or 0) + (um.get("thoughtsTokenCount", 0) or 0)
        text = ""
        try:
            text = "".join(p.get("text", "") for p in js["candidates"][0]["content"]["parts"] if not p.get("thought"))
        except Exception:
            pass
        rec = {"label": label, "model_requested": model, "model_version_returned": js.get("modelVersion") if isinstance(js, dict) else None,
               "http_status": status, "t_utc": t_utc, "t_seattle": t_sea, "elapsed_s": elapsed,
               "system_instruction": system, "prompt": prompt, "prompt_sha256": sha256_text(prompt),
               "generation_config": gen_cfg, "usage_metadata": um, "finish_reason": _finish(js),
               "response_text": text, "response_raw": js,
               "epistemic_status": "model-opinion; not verified truth"}
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / f"{label or 'call'}.json").write_text(json.dumps(redact(rec), indent=1, ensure_ascii=False) + "\n")
        led["calls"] += 1; led["input_tokens"] += used_in; led["output_tokens"] += used_out
        led["entries"].append({"label": label, "model": model, "http_status": status, "t_utc": t_utc,
                               "input_tokens": used_in, "output_tokens_incl_thinking": used_out, "usage_metadata": um})
        _save_ledger(led)
        if status != 200:
            raise RuntimeError(f"generateContent HTTP {status}: {json.dumps(redact(js))[:500]}")
        return rec


def _finish(js):
    try:
        return js["candidates"][0].get("finishReason")
    except Exception:
        return None
