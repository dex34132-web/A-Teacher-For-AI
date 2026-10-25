"""Minimal LLM client for Toolio — stdlib only, auto-detecting, graceful fallback.

Tools that need judgment (confidence, conflict, dedup, quantify, lifecycle,
routing) can call :func:`llm_complete` to ask the configured model. When no
model is configured, or the call fails, the helper returns ``None`` and the
caller falls back to its existing heuristic. This keeps every tool working
offline and in tests, while letting a real model improve decisions when one
is available.

Auto-detection order (first hit wins):
    1. Explicit env vars: TOOLIO_LLM_BASE_URL / TOOLIO_LLM_MODEL / TOOLIO_LLM_API_KEY
    2. OpenCode config (~/.config/opencode/opencode.jsonc or opencode.json):
       reads the top-level "model" ("provider/model") and the matching
       provider's baseURL + apiKey (supports env://VAR references).
    3. Ollama at http://localhost:11434 (first available model).
    4. None (disabled) — tools use heuristics.

Override knobs:
    TOOLIO_LLM_BASE_URL   OpenAI-compatible base URL
    TOOLIO_LLM_MODEL      Model name
    TOOLIO_LLM_API_KEY    API key (empty -> disabled)
    TOOLIO_LLM_TIMEOUT    Request timeout seconds (default 20)
    TOOLIO_LLM_ENABLED    "0"/"false" to force-disable even with a key
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from typing import Any


def _env(name: str, default: str = "") -> str:
    return (os.environ.get(name) or default).strip()


def _strip_jsonc(text: str) -> str:
    """Remove // and /* */ comments and trailing commas from JSONC.

    String-aware: '//' inside a quoted string (e.g. https://) is preserved.
    """
    out = []
    i = 0
    n = len(text)
    in_str = False
    while i < n:
        ch = text[i]
        if in_str:
            if ch == "\\" and i + 1 < n:
                out.append(text[i:i + 2])
                i += 2
                continue
            if ch == '"':
                in_str = False
            out.append(ch)
            i += 1
            continue
        # not in string
        if ch == '"':
            in_str = True
            out.append(ch)
            i += 1
            continue
        if ch == "/" and i + 1 < n and text[i + 1] == "*":
            j = text.find("*/", i + 2)
            if j < 0:
                break
            i = j + 2
            continue
        if ch == "/" and i + 1 < n and text[i + 1] == "/":
            # skip to end of line
            j = text.find("\n", i)
            if j < 0:
                break
            i = j
            continue
        out.append(ch)
        i += 1
    text = "".join(out)
    # Remove trailing commas before } or ]
    text = re.sub(r",(\s*[}\]])", r"\1", text)
    return text


def _read_opencode_config() -> dict[str, Any] | None:
    """Try to read OpenCode's config file. Returns parsed dict or None."""
    candidates = []
    home = os.path.expanduser("~")
    for base in (os.path.join(home, ".config", "opencode"), os.path.join(home, ".opencode")):
        for name in ("opencode.jsonc", "opencode.json"):
            candidates.append(os.path.join(base, name))
    for path in candidates:
        try:
            with open(path, "r", encoding="utf-8-sig") as f:
                raw = f.read()
        except (OSError, IOError):
            continue
        try:
            return json.loads(_strip_jsonc(raw))
        except (json.JSONDecodeError, ValueError):
            continue
    return None


def _resolve_ref(ref: str) -> str:
    """Resolve env://VAR or file:// references; otherwise return as-is."""
    ref = (ref or "").strip()
    if ref.startswith("env://"):
        var = ref[len("env://"):]
        return (os.environ.get(var) or "").strip()
    if ref.startswith("auth://"):
        provider = ref[len("auth://"):]
        return _auth_key(provider)
    if ref.startswith("file://"):
        path = ref[len("file://"):]
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read().strip()
        except (OSError, IOError):
            return ""
    return ref


def _auth_key(provider: str) -> str:
    """Look up an API key for ``provider`` in OpenCode's auth.json."""
    if not provider:
        return ""
    home = os.path.expanduser("~")
    candidates = [
        os.path.join(home, ".local", "share", "opencode", "auth.json"),
        os.path.join(home, ".config", "opencode", "auth.json"),
    ]
    for path in candidates:
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, IOError, json.JSONDecodeError, ValueError):
            continue
        if isinstance(data, dict):
            entry = data.get(provider)
            if isinstance(entry, dict):
                key = entry.get("key") or entry.get("apiKey") or entry.get("access")
                if isinstance(key, str) and key.strip():
                    return key.strip()
    return ""


def _detect_from_opencode() -> tuple[str, str, str] | None:
    """Return (base_url, model, api_key) from OpenCode config, or None."""
    cfg = _read_opencode_config()
    if not isinstance(cfg, dict):
        return None
    model_spec = cfg.get("model")
    if not isinstance(model_spec, str) or not model_spec.strip():
        return None
    model_spec = model_spec.strip()
    # model spec is "provider/model" or just "model"
    if "/" in model_spec:
        provider_name, model_name = model_spec.split("/", 1)
    else:
        provider_name, model_name = "", model_spec
    providers = cfg.get("provider")
    base_url = ""
    api_key = ""
    if isinstance(providers, dict) and provider_name and provider_name in providers:
        prov = providers[provider_name]
        if isinstance(prov, dict):
            opts = prov.get("options")
            if isinstance(opts, dict):
                base_url = _resolve_ref(str(opts.get("baseURL", "") or ""))
                api_key = _resolve_ref(str(opts.get("apiKey", "") or ""))
            # model may be nested under provider.models
            models = prov.get("models")
            if isinstance(models, dict) and model_name in models:
                m = models[model_name]
                if isinstance(m, dict) and "id" in m:
                    model_name = str(m["id"])
    if not base_url:
        # Fallback: try top-level baseURL
        base_url = _resolve_ref(str(cfg.get("baseURL", "") or ""))
    if not api_key:
        api_key = _resolve_ref(str(cfg.get("apiKey", "") or ""))
    if not api_key:
        api_key = _auth_key(provider_name)
    if not base_url or not model_name:
        return None
    return base_url.rstrip("/"), model_name, api_key


def _detect_from_ollama() -> tuple[str, str, str] | None:
    """Probe local Ollama. Returns (base_url, model, api_key) or None."""
    try:
        req = urllib.request.Request("http://localhost:11434/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=2) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception:  # noqa: BLE001
        return None
    models = data.get("models") if isinstance(data, dict) else None
    if not isinstance(models, list) or not models:
        return None
    first = models[0]
    name = first.get("name") if isinstance(first, dict) else None
    if not isinstance(name, str) or not name:
        return None
    return "http://localhost:11434/v1", name, ""


def _detect() -> tuple[str, str, str] | None:
    """Return (base_url, model, api_key) from the best available source, or None."""
    # 1. Explicit env vars
    base = _env("TOOLIO_LLM_BASE_URL")
    model = _env("TOOLIO_LLM_MODEL")
    key = _env("TOOLIO_LLM_API_KEY")
    if base and model:
        return base.rstrip("/"), model, key
    # 2. OpenCode config
    oc = _detect_from_opencode()
    if oc is not None:
        b, m, k = oc
        # Allow env overrides to fill gaps
        if not base:
            base = b
        if not model:
            model = m
        if not key:
            key = k
        if base and model:
            return base.rstrip("/"), model, key
    # 3. Ollama
    ol = _detect_from_ollama()
    if ol is not None and not base and not model:
        return ol
    # 4. Partial: env model without base -> can't call
    return None


def llm_detect() -> dict[str, Any]:
    """Public: return a dict describing what was detected (for debugging/tests)."""
    res = _detect()
    if res is None:
        return {"available": False, "base_url": "", "model": "", "api_key": ""}
    base, model, key = res
    return {
        "available": bool(key or base.startswith("http://localhost")),
        "base_url": base,
        "model": model,
        "api_key": "***" if key else "",
    }


def llm_available() -> bool:
    """True when an LLM is configured and not explicitly disabled."""
    if _env("TOOLIO_LLM_ENABLED", "1").lower() in {"0", "false", "no", "off"}:
        return False
    # Explicit disable via env
    res = _detect()
    if res is None:
        return False
    _, _, key = res
    base, _, _ = res
    # Ollama needs no key
    if base.startswith("http://localhost") or base.startswith("http://127.0.0.1"):
        return True
    return bool(key)


def _base_url() -> str:
    res = _detect()
    if res is None:
        return _env("TOOLIO_LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    return res[0]


def _model() -> str:
    res = _detect()
    if res is None:
        return _env("TOOLIO_LLM_MODEL", "gpt-4o-mini")
    return res[1]


def _api_key() -> str:
    res = _detect()
    if res is None:
        return _env("TOOLIO_LLM_API_KEY", "")
    return res[2]


def _timeout() -> float:
    try:
        return float(_env("TOOLIO_LLM_TIMEOUT", "20") or "20")
    except ValueError:
        return 20.0


def llm_complete(
    prompt: str,
    *,
    system: str = "",
    temperature: float = 0.2,
    max_tokens: int = 256,
) -> str | None:
    """Return the model's text reply, or ``None`` if unavailable/failed.

    Never raises. Callers must treat ``None`` as "use the heuristic".
    """
    if not llm_available():
        return None
    base = _base_url()
    model = _model()
    key = _api_key()
    url = base + "/chat/completions"
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    data = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if key:
        headers["Authorization"] = "Bearer " + key
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=_timeout()) as resp:
            raw = resp.read().decode("utf-8")
    except Exception:  # noqa: BLE001
        return None
    try:
        obj = json.loads(raw)
        choices = obj.get("choices") if isinstance(obj, dict) else None
        if not isinstance(choices, list) or not choices:
            return None
        msg = choices[0].get("message") if isinstance(choices[0], dict) else None
        if not isinstance(msg, dict):
            return None
        content = msg.get("content")
        return content if isinstance(content, str) else None
    except (json.JSONDecodeError, ValueError, AttributeError, TypeError):
        return None


def llm_judge(prompt: str, *, system: str = "", options: list[str] | None = None) -> str | None:
    """Ask the model to pick one of ``options``; return the chosen option or None."""
    opts = options or []
    if not opts:
        return None
    reply = llm_complete(
        prompt + "\nOptions: " + ", ".join(opts) + "\nReply with one option only.",
        system=system or "You are a judge. Reply with one of the given options.",
        temperature=0.0,
        max_tokens=16,
    )
    if reply is None:
        return None
    low = reply.strip().lower()
    for o in opts:
        if low == o.lower() or low.startswith(o.lower()):
            return o
    return None
