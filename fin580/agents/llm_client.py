"""Provider abstraction + cache layer for all LLM calls (spec Sections 4.2, 5.5, 8)."""

from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from pathlib import Path
from typing import Any

# Auto-load .env so any code path that uses chat() picks up provider keys.
try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv(Path(__file__).resolve().parents[2] / ".env")
except ImportError:
    pass

CACHE_ROOT = Path(__file__).resolve().parents[2] / "runs" / "_global_cache"
CACHE_ROOT.mkdir(parents=True, exist_ok=True)

PROVIDER_MIN_INTERVAL_SECONDS = {
    "cerebras": float(os.environ.get("CEREBRAS_MIN_INTERVAL_SECONDS", "2.0")),
}
_provider_last_call_at: dict[str, float] = {}
_provider_rate_lock = threading.Lock()


def _canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


def _cache_key(*, prompt: str, input_json: dict, model_id: str,
                model_version: str = "", temperature: float) -> str:
    """Cache key per spec Section 5.5 + 8.2: includes model_version so a
    pinned-version change automatically invalidates the cache for that agent."""
    payload = (
        f"{prompt}\n{_canonical_json(input_json)}\n"
        f"{model_id}\n{model_version}\n{temperature}"
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _route_provider(model_id: str) -> str:
    """Provider routing per spec Section 4.2 (DL #53 — Cerebras model
    substitution: free tier hosts gpt-oss / qwen-3 / zai-glm / llama3.1
    instead of deepseek-r1 originally specified).

    Anchored matches in deterministic precedence:
      - HF: qwen/, /qwen, mistralai/, meta-llama/
      - Groq: llama-*, groq/*
      - Cerebras: deepseek*, gpt-oss*, qwen-3*, zai-glm*, llama3.1*
        (these are the actual free-tier model IDs on Cerebras as of 2026)

    Anthropic / Claude is NOT used in the headline run and raises so that any
    stray `claude-*` model_id fails fast rather than silently routing to an
    undefined caller.
    """
    m = model_id.lower()
    # HuggingFace: explicit org/model prefixes
    if (
        m.startswith("qwen/")
        or "/qwen" in m
        or m.startswith("mistralai/")
        or m.startswith("meta-llama/")
        or m.startswith("deepseek-ai/")  # DeepSeek R1 + Distill variants on HF
    ):
        return "huggingface"
    if m.startswith("llama-") or m.startswith("groq/"):
        return "groq"
    # Cerebras free tier (DL #53): bare model IDs without org prefix
    if (
        m.startswith("deepseek-r1")  # Cerebras-style (no org prefix)
        or m.startswith("gpt-oss")
        or m.startswith("qwen-3")
        or m.startswith("zai-")
        or m.startswith("llama3.1-")
    ):
        return "cerebras"
    raise ValueError(
        f"Cannot route model_id={model_id!r}. "
        "Supported prefixes: qwen/, mistralai/, meta-llama/, deepseek-ai/ (HF); "
        "llama-, groq/ (Groq); deepseek-r1*, gpt-oss*, qwen-3*, zai-*, llama3.1-* (Cerebras)."
    )


def _throttle_provider(provider: str) -> None:
    """Apply provider-scoped minimum request spacing for uncached LLM calls."""
    min_interval = PROVIDER_MIN_INTERVAL_SECONDS.get(provider, 0.0)
    if min_interval <= 0:
        return

    with _provider_rate_lock:
        now = time.monotonic()
        next_allowed_at = _provider_last_call_at.get(provider, 0.0) + min_interval
        if now < next_allowed_at:
            time.sleep(next_allowed_at - now)
            now = time.monotonic()
        _provider_last_call_at[provider] = now


def _extract_json(text: str) -> str:
    """Pull the first JSON object out of a possibly-noisy LLM response.

    Handles:
      - Markdown ```json fences
      - DeepSeek R1 / similar reasoning-model <think>...</think> blocks
        (strip the entire reasoning trace before JSON extraction)
    """
    import re

    # Strip <think>...</think> blocks (DeepSeek R1 reasoning trace).
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    text = text.strip()
    if text.startswith("```"):
        parts = text.split("```")
        if len(parts) >= 2:
            text = parts[1]
            if text.startswith("json"):
                text = text[4:]
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"No JSON object found in response: {text[:200]}")
    return text[start : end + 1]


def _call_huggingface(prompt: str, input_json: dict, model_id: str,
                       temperature: float) -> dict:
    from huggingface_hub import InferenceClient  # type: ignore
    token = os.environ["HF_TOKEN"]
    client = InferenceClient(model=model_id, token=token)
    full_prompt = f"{prompt}\n\nINPUT:\n{_canonical_json(input_json)}"
    resp = client.chat_completion(
        messages=[{"role": "user", "content": full_prompt}],
        temperature=temperature,
        max_tokens=1500,
    )
    text = resp.choices[0].message.content
    return json.loads(_extract_json(text))


def _call_groq(prompt: str, input_json: dict, model_id: str,
                temperature: float) -> dict:
    from groq import Groq  # type: ignore
    client = Groq(api_key=os.environ["GROQ_API_KEY"])
    full_prompt = f"{prompt}\n\nINPUT:\n{_canonical_json(input_json)}"
    resp = client.chat.completions.create(
        model=model_id,
        messages=[{"role": "user", "content": full_prompt}],
        temperature=temperature,
        max_tokens=1500,
        response_format={"type": "json_object"},
    )
    text = resp.choices[0].message.content
    return json.loads(_extract_json(text))


def _call_cerebras(prompt: str, input_json: dict, model_id: str,
                    temperature: float) -> dict:
    from cerebras.cloud.sdk import Cerebras  # type: ignore
    client = Cerebras(api_key=os.environ["CEREBRAS_API_KEY"])
    full_prompt = f"{prompt}\n\nINPUT:\n{_canonical_json(input_json)}"
    resp = client.chat.completions.create(
        model=model_id,
        messages=[{"role": "user", "content": full_prompt}],
        temperature=temperature,
        max_tokens=1500,
    )
    text = resp.choices[0].message.content
    return json.loads(_extract_json(text))


def chat(*, prompt: str, input_json: dict, model_id: str,
          model_version: str = "", temperature: float = 0.0,
          max_retries: int = 2) -> dict:
    """Cached LLM call. Returns parsed JSON. Spec Sections 4.2, 5.5, 8.2."""
    key = _cache_key(
        prompt=prompt, input_json=input_json, model_id=model_id,
        model_version=model_version, temperature=temperature,
    )
    cache_file = CACHE_ROOT / f"{key}.json"
    if cache_file.exists():
        return json.loads(cache_file.read_text())["response"]

    provider = _route_provider(model_id)
    callers = {
        "huggingface": _call_huggingface,
        "groq": _call_groq,
        "cerebras": _call_cerebras,
    }
    last_err = None
    for attempt in range(max_retries):
        try:
            _throttle_provider(provider)
            response = callers[provider](prompt, input_json, model_id, temperature)
            payload = json.dumps(
                {
                    "response": response,
                    "provider": provider,
                    "model_id": model_id,
                    "model_version": model_version,
                    "temperature": temperature,
                    "timestamp": time.time(),
                },
                indent=2,
            )
            # Atomic write: write to temp file in same dir, then rename.
            tmp_file = cache_file.with_suffix(cache_file.suffix + ".tmp")
            tmp_file.write_text(payload)
            os.replace(tmp_file, cache_file)
            return response
        except (ValueError, json.JSONDecodeError) as e:
            last_err = e
            if attempt < max_retries - 1:
                continue
            raise
        except Exception as e:
            last_err = e
            # Per Codex Round-9: providers like Groq enforce 60-second
            # RPM windows; original 5/30/120s backoff was too tight.
            # New: 30s, 90s, 300s, 600s (max retries fixed at 3, so the
            # 600s tier only matters if max_retries is bumped).
            wait_schedule = [30, 90, 300, 600]
            wait = wait_schedule[min(attempt, len(wait_schedule) - 1)]
            time.sleep(wait)
    raise RuntimeError(f"LLM call failed after {max_retries} attempts: {last_err}")
