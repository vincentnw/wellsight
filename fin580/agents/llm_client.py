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
    "gemini": float(os.environ.get("GEMINI_MIN_INTERVAL_SECONDS", "4.0")),
    "openai": float(os.environ.get("OPENAI_MIN_INTERVAL_SECONDS", "0.5")),
}
_provider_last_call_at: dict[str, float] = {}
_provider_rate_lock = threading.Lock()


def _cerebras_keys() -> list[str]:
    """Collect all configured Cerebras keys for round-robin rotation.

    Reads CEREBRAS_API_KEY (primary) and any CEREBRAS_API_KEY_2,
    CEREBRAS_API_KEY_3, etc. Returns the keys in deterministic order.
    Round-robin across multiple keys halves per-account 429 contention
    on free tier without changing model quality."""
    keys = []
    primary = os.environ.get("CEREBRAS_API_KEY", "").strip()
    if primary:
        keys.append(primary)
    # Discover numbered fallback keys
    i = 2
    while True:
        k = os.environ.get(f"CEREBRAS_API_KEY_{i}", "").strip()
        if not k:
            break
        keys.append(k)
        i += 1
    return keys


# Round-robin counter for Cerebras key rotation (thread-safe).
_cerebras_call_counter = 0
_cerebras_key_lock = threading.Lock()


def _next_cerebras_key() -> str:
    """Pick the next Cerebras key in round-robin order.
    Falls back to single-key mode if only one is configured."""
    global _cerebras_call_counter
    keys = _cerebras_keys()
    if not keys:
        raise RuntimeError("No CEREBRAS_API_KEY configured.")
    if len(keys) == 1:
        return keys[0]
    with _cerebras_key_lock:
        idx = _cerebras_call_counter % len(keys)
        _cerebras_call_counter += 1
    return keys[idx]


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
    # Gemini via Google AI Studio (added by Agent 4+5 redesign for cross-provider Arbiter)
    if m.startswith("gemini-") or m.startswith("models/gemini-"):
        return "gemini"
    # OpenAI: gpt-* (mini, full, etc.)
    if m.startswith("gpt-") or m.startswith("o1-") or m.startswith("o3-"):
        return "openai"
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
        "llama-, groq/ (Groq); gemini-* (Google AI Studio); "
        "gpt-*, o1-*, o3-* (OpenAI); "
        "deepseek-r1*, gpt-oss*, qwen-3*, zai-*, llama3.1-* (Cerebras)."
    )


def _throttle_provider(provider: str, *, scope_key: str | None = None) -> None:
    """Apply minimum request spacing for uncached LLM calls.

    `scope_key` is an optional sub-key (e.g., individual Cerebras account ID)
    so multiple keys in a round-robin pool can each have independent throttle
    timing. Without scope_key, throttling is per-provider (legacy behaviour)."""
    min_interval = PROVIDER_MIN_INTERVAL_SECONDS.get(provider, 0.0)
    if min_interval <= 0:
        return

    key = f"{provider}:{scope_key}" if scope_key else provider
    with _provider_rate_lock:
        now = time.monotonic()
        next_allowed_at = _provider_last_call_at.get(key, 0.0) + min_interval
        if now < next_allowed_at:
            time.sleep(next_allowed_at - now)
            now = time.monotonic()
        _provider_last_call_at[key] = now


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
        max_tokens=3000,
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
        max_tokens=3000,
        response_format={"type": "json_object"},
    )
    text = resp.choices[0].message.content
    return json.loads(_extract_json(text))


def _call_cerebras(prompt: str, input_json: dict, model_id: str,
                    temperature: float) -> dict:
    """Round-robin across configured Cerebras keys (CEREBRAS_API_KEY,
    CEREBRAS_API_KEY_2, ...). With N keys, effective throughput on free
    tier is roughly N× since each account has its own queue. Per-key
    throttling ensures each key independently respects CEREBRAS_MIN_INTERVAL_SECONDS."""
    from cerebras.cloud.sdk import Cerebras  # type: ignore
    api_key = _next_cerebras_key()
    # Per-key throttle (each Cerebras account has its own queue/rate window)
    _throttle_provider("cerebras", scope_key=api_key[-12:])  # tail of key as scope id
    client = Cerebras(api_key=api_key)
    full_prompt = f"{prompt}\n\nINPUT:\n{_canonical_json(input_json)}"
    resp = client.chat.completions.create(
        model=model_id,
        messages=[{"role": "user", "content": full_prompt}],
        temperature=temperature,
        max_tokens=3000,
    )
    text = resp.choices[0].message.content
    return json.loads(_extract_json(text))


def _call_openai(prompt: str, input_json: dict, model_id: str,
                  temperature: float) -> dict:
    """OpenAI Chat Completions API. Used for gpt-4o-mini (Agent 2/4/Bull/Bear)
    and gpt-5.4-mini (Arbiter) per docs/AGENT4_5_REDESIGN.md cost-optimized
    stack. Per-request rate limits are typically high enough that the
    OPENAI_MIN_INTERVAL_SECONDS throttle (default 0.5s) is enough.

    Two API quirks handled:
      - gpt-5.* and o-series models require `max_completion_tokens` (because
        they spend tokens on reasoning before output); gpt-4o family uses
        legacy `max_tokens`.
      - Reasoning models don't accept the `temperature` param at all on some
        SDK versions; we drop it on retry if rejected.
    """
    from openai import OpenAI  # type: ignore
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    full_prompt = f"{prompt}\n\nINPUT:\n{_canonical_json(input_json)}"

    is_reasoning_model = (
        model_id.startswith("gpt-5") or model_id.startswith("o1") or model_id.startswith("o3")
    )
    kwargs: dict = {
        "model": model_id,
        "messages": [{"role": "user", "content": full_prompt}],
    }
    # Token budget — different param name for reasoning vs legacy chat models.
    if is_reasoning_model:
        kwargs["max_completion_tokens"] = 3000
    else:
        kwargs["max_tokens"] = 3000
        kwargs["temperature"] = temperature  # reasoning models often reject this
    # Strict JSON output mode reduces parse failures on mini-tier models.
    kwargs["response_format"] = {"type": "json_object"}

    try:
        resp = client.chat.completions.create(**kwargs)
    except Exception:
        # If the model rejects response_format or temperature, retry without those.
        kwargs.pop("response_format", None)
        kwargs.pop("temperature", None)
        resp = client.chat.completions.create(**kwargs)
    text = resp.choices[0].message.content
    return json.loads(_extract_json(text))


def _call_gemini(prompt: str, input_json: dict, model_id: str,
                  temperature: float) -> dict:
    """Google AI Studio Gemini API. Free tier limits as of 2026:
        gemini-2.0-flash:  15 RPM, 1500 RPD
        gemini-2.5-flash:  10 RPM,  250 RPD
        gemini-2.5-pro:     5 RPM,  100 RPD
    For the Agent 5 Arbiter role we default to gemini-2.0-flash (1500 RPD
    fits the 200-cell ablation matrix comfortably)."""
    try:
        # Newer SDK (recommended as of 2025+). Requires `pip install google-genai`.
        from google import genai
        client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
        full_prompt = f"{prompt}\n\nINPUT:\n{_canonical_json(input_json)}"
        resp = client.models.generate_content(
            model=model_id,
            contents=full_prompt,
            config={"temperature": temperature, "max_output_tokens": 3000},
        )
        text = resp.text
        return json.loads(_extract_json(text))
    except ImportError:
        # Older SDK fallback. Requires `pip install google-generativeai`.
        import google.generativeai as genai_old  # type: ignore
        genai_old.configure(api_key=os.environ["GEMINI_API_KEY"])
        full_prompt = f"{prompt}\n\nINPUT:\n{_canonical_json(input_json)}"
        model = genai_old.GenerativeModel(model_id)
        resp = model.generate_content(
            full_prompt,
            generation_config={"temperature": temperature, "max_output_tokens": 3000},
        )
        text = resp.text
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
        "gemini": _call_gemini,
        "openai": _call_openai,
    }
    last_err = None
    for attempt in range(max_retries):
        try:
            # Cerebras handles its own per-key throttling inside _call_cerebras
            # (each rotating key has independent rate timing). Other providers
            # use the simpler provider-level throttle here.
            if provider != "cerebras":
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
