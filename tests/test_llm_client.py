from fin580.agents.llm_client import _cache_key, _route_provider


def test_cache_key_deterministic():
    k1 = _cache_key(prompt="P", input_json={"a": 1}, model_id="qwen/x", temperature=0.0)
    k2 = _cache_key(prompt="P", input_json={"a": 1}, model_id="qwen/x", temperature=0.0)
    assert k1 == k2 and len(k1) == 64


def test_cache_key_input_sensitive():
    k1 = _cache_key(prompt="P", input_json={"a": 1}, model_id="qwen/x", temperature=0.0)
    k2 = _cache_key(prompt="P", input_json={"a": 2}, model_id="qwen/x", temperature=0.0)
    assert k1 != k2


def test_cache_key_model_version_sensitive():
    k1 = _cache_key(prompt="P", input_json={"a": 1}, model_id="qwen/x",
                    model_version="v1", temperature=0.0)
    k2 = _cache_key(prompt="P", input_json={"a": 1}, model_id="qwen/x",
                    model_version="v2", temperature=0.0)
    assert k1 != k2


def test_route_provider_qwen():
    assert _route_provider("Qwen/Qwen2.5-72B-Instruct") == "huggingface"


def test_route_provider_llama():
    assert _route_provider("llama-3.3-70b-versatile") == "groq"


def test_route_provider_deepseek():
    assert _route_provider("deepseek-r1") == "cerebras"


def test_route_provider_cerebras_free_tier_models():
    # Per DL #53, Cerebras free tier hosts these (bare prefixes)
    assert _route_provider("gpt-oss-120b") == "cerebras"
    assert _route_provider("qwen-3-235b-a22b-instruct-2507") == "cerebras"
    assert _route_provider("zai-glm-4.7") == "cerebras"
    assert _route_provider("llama3.1-8b") == "cerebras"


def test_route_provider_deepseek_ai_to_hf():
    # Per DL #53 follow-up: DeepSeek R1 routed via HF (deepseek-ai/* prefix)
    assert _route_provider("deepseek-ai/DeepSeek-R1") == "huggingface"
    assert _route_provider("deepseek-ai/DeepSeek-R1-Distill-Llama-70B") == "huggingface"


def test_extract_json_strips_think_block():
    from fin580.agents.llm_client import _extract_json
    raw = (
        "<think>The user wants a JSON object. I'll return ok=true.</think>\n"
        '{"ok": true}'
    )
    assert _extract_json(raw) == '{"ok": true}'


def test_route_provider_claude_raises():
    import pytest
    with pytest.raises(ValueError):
        _route_provider("claude-sonnet-4-6")


def test_route_provider_meta_llama_to_hf():
    assert _route_provider("meta-llama/Llama-3.3-70B-Instruct") == "huggingface"


def test_route_provider_unknown_raises():
    import pytest
    # An entirely unknown model_id should raise. (`gpt-4` was used as the
    # unknown sentinel before v2.5; it is now a real OpenAI model.)
    with pytest.raises(ValueError):
        _route_provider("totally-unknown-model-xyz")


def test_route_provider_openai_models():
    """v2.5 routing: gpt-4*, gpt-5*, o1-*, o3-* go to OpenAI.
    gpt-oss-* must continue to route to Cerebras (it's their hosted
    open-source GPT model, not OpenAI's namespace)."""
    assert _route_provider("gpt-4o-mini") == "openai"
    assert _route_provider("gpt-4") == "openai"
    assert _route_provider("gpt-5-mini") == "openai"
    assert _route_provider("o1-mini") == "openai"
    assert _route_provider("o3-mini") == "openai"
    # gpt-oss must stay on Cerebras even though name starts with "gpt-"
    assert _route_provider("gpt-oss-120b") == "cerebras"


def test_preflight_models_reports_missing_sdk(monkeypatch):
    import importlib
    import pytest

    from fin580.agents.llm_client import preflight_models

    monkeypatch.setenv("CEREBRAS_API_KEY", "x")
    real_import = importlib.import_module

    def fake_import(name):
        if name == "cerebras.cloud.sdk":
            raise ModuleNotFoundError("No module named 'cerebras'")
        return real_import(name)

    monkeypatch.setattr(importlib, "import_module", fake_import)
    with pytest.raises(RuntimeError, match="cerebras"):
        preflight_models(["qwen-3-235b-a22b-instruct-2507"])


def test_preflight_models_reports_missing_key(monkeypatch):
    import pytest

    from fin580.agents.llm_client import preflight_models

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        preflight_models(["gpt-4o-mini"])
