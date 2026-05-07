"""Tiny probe of each LLM provider before the live anchor smoke test.

Sends a 5-word prompt to each, asks for a 5-word JSON response, and reports
status. Costs < $0.01 per provider on free tiers.

Usage:
    python -m scripts.probe_providers
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")


def probe_hf() -> tuple[bool, str]:
    token = os.environ.get("HF_TOKEN", "")
    if not token:
        return False, "HF_TOKEN missing in .env"
    try:
        from huggingface_hub import InferenceClient
        client = InferenceClient(model="Qwen/Qwen2.5-72B-Instruct", token=token)
        resp = client.chat_completion(
            messages=[{"role": "user", "content": 'Say {"ok": true} as JSON.'}],
            temperature=0.0, max_tokens=20,
        )
        text = resp.choices[0].message.content
        return True, f"Qwen 72B: {text.strip()[:60]}"
    except Exception as e:
        msg = str(e)[:160]
        # If 72B isn't on the free tier, try 32B fallback
        if "rate" in msg.lower() or "not found" in msg.lower() or "402" in msg or "404" in msg:
            try:
                client = InferenceClient(model="Qwen/Qwen2.5-32B-Instruct", token=token)
                resp = client.chat_completion(
                    messages=[{"role": "user", "content": 'Say {"ok": true} as JSON.'}],
                    temperature=0.0, max_tokens=20,
                )
                text = resp.choices[0].message.content
                return True, f"Qwen 32B fallback: {text.strip()[:60]}"
            except Exception as e2:
                return False, f"HF 72B failed: {msg}; 32B fallback also failed: {str(e2)[:80]}"
        return False, f"HF: {msg}"


def probe_groq() -> tuple[bool, str]:
    key = os.environ.get("GROQ_API_KEY", "")
    if not key:
        return False, "GROQ_API_KEY missing in .env"
    try:
        from groq import Groq
        client = Groq(api_key=key)
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": 'Say {"ok": true} as JSON.'}],
            temperature=0.0, max_tokens=20,
            response_format={"type": "json_object"},
        )
        text = resp.choices[0].message.content
        return True, f"Llama 70B: {text.strip()[:60]}"
    except Exception as e:
        return False, f"Groq: {str(e)[:160]}"


def probe_arbiter_hf() -> tuple[bool, str]:
    """Per DL #53: Arbiter is routed via HuggingFace, not Cerebras."""
    token = os.environ.get("HF_TOKEN", "")
    if not token:
        return False, "HF_TOKEN missing in .env"
    try:
        from huggingface_hub import InferenceClient
        client = InferenceClient(
            model="deepseek-ai/DeepSeek-R1-Distill-Llama-70B", token=token
        )
        resp = client.chat_completion(
            messages=[{"role": "user", "content": 'Say {"ok": true} as JSON.'}],
            temperature=0.0, max_tokens=40,
        )
        text = resp.choices[0].message.content
        return True, f"DeepSeek-R1-Distill-Llama-70B: {text.strip()[:80]}"
    except Exception as e:
        return False, f"HF DeepSeek: {str(e)[:160]}"


def main() -> int:
    print("=" * 70)
    print("PROBING LLM PROVIDERS (small calls, costs ~$0)")
    print("=" * 70)
    results = {}
    for name, fn in [("HF Qwen 72B (Bull / Agent 2)", probe_hf),
                     ("Groq Llama 70B (Bear / Agent 3 / Agent 4)", probe_groq),
                     ("HF DeepSeek-R1 distill (Arbiter)", probe_arbiter_hf)]:
        print(f"\n{name}...")
        ok, msg = fn()
        status = "OK   " if ok else "FAIL "
        print(f"  [{status}] {msg}")
        results[name] = (ok, msg)
    print("\n" + "=" * 70)
    n_ok = sum(1 for ok, _ in results.values() if ok)
    print(f"{n_ok}/{len(results)} providers OK")
    return 0 if n_ok == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
