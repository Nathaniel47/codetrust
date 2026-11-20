import json

import httpx
import pytest

from codetrust.llm.budget import DailyBudgetExhausted, TokenBudget
from codetrust.llm.cache import ResponseCache
from codetrust.llm.client import LLMClient
from codetrust.llm.providers import ProviderError, list_model_ids, make_backend


def counting_backend():
    calls = []

    def backend(model, messages, temperature, seed, max_tokens):
        calls.append((model, messages, temperature, seed, max_tokens))
        return f"answer {len(calls)}", 10

    return backend, calls


def make_client(tmp_path, **kw):
    backend, calls = counting_backend()
    client = LLMClient(backend, "p", "m", 0.2, 7, 100, cache=ResponseCache(tmp_path), **kw)
    return client, calls


def test_second_identical_call_is_served_from_cache(tmp_path):
    client, calls = make_client(tmp_path)
    first = client.complete("hello", system="sys")
    assert client.complete("hello", system="sys") == first
    assert len(calls) == 1 and client.cache_hits == 1 and client.tokens_used == 10
    assert calls[0][2:] == (0.2, 7, 100)


def test_repeat_number_gives_an_independent_sample(tmp_path):
    client, calls = make_client(tmp_path)
    client.complete("hello", repeat=0)
    client.complete("hello", repeat=1)
    assert len(calls) == 2


def test_budget_stops_before_calling_the_backend(tmp_path):
    budget = TokenBudget(tmp_path / "b", "m", {"rpm": 5, "tpm": 10_000, "rpd": 1, "tpd": 100})
    client, calls = make_client(tmp_path / "c", budget=budget)
    with pytest.raises(DailyBudgetExhausted):
        client.complete("x" * 400)
    assert calls == []


def mock(handler):
    return httpx.MockTransport(handler)


def test_openai_compatible_request_and_parse(monkeypatch):
    monkeypatch.setenv("CODETRUST_GROQ_API_KEY", "test-key")
    seen = {}

    def handler(request):
        seen["url"], seen["auth"] = str(request.url), request.headers["authorization"]
        seen["body"] = json.loads(request.content)
        reply = {"choices": [{"message": {"content": "hi"}}], "usage": {"total_tokens": 42}}
        return httpx.Response(200, json=reply)

    backend = make_backend("groq", transport=mock(handler))
    text, tokens = backend("m1", [{"role": "user", "content": "q"}], 0.2, 5, 300)
    assert (text, tokens) == ("hi", 42)
    assert seen["url"] == "https://api.groq.com/openai/v1/chat/completions"
    assert seen["auth"] == "Bearer test-key"
    assert seen["body"]["seed"] == 5 and seen["body"]["max_tokens"] == 300
    assert "test-key" not in seen["url"]


def test_gemini_key_goes_in_header_not_url(monkeypatch):
    monkeypatch.setenv("CODETRUST_GEMINI_API_KEY", "gem-key")
    seen = {}

    def handler(request):
        seen["url"], seen["header"] = str(request.url), request.headers["x-goog-api-key"]
        seen["body"] = json.loads(request.content)
        body = {
            "candidates": [{"content": {"parts": [{"text": "a"}, {"text": "b"}]}}],
            "usageMetadata": {"totalTokenCount": 9},
        }
        return httpx.Response(200, json=body)

    backend = make_backend("gemini", transport=mock(handler))
    messages = [{"role": "system", "content": "s"}, {"role": "user", "content": "q"}]
    assert backend("g", messages, 0.2, 1, 50) == ("ab", 9)
    assert "gem-key" not in seen["url"] and seen["header"] == "gem-key"
    assert seen["body"]["systemInstruction"]["parts"][0]["text"] == "s"
    assert seen["body"]["generationConfig"]["seed"] == 1


def test_rate_limit_is_retried_then_succeeds(monkeypatch):
    monkeypatch.setenv("CODETRUST_MISTRAL_API_KEY", "k")
    answers = iter([429, 429, 200])
    waits = []

    def handler(request):
        if next(answers) == 429:
            return httpx.Response(429, headers={"retry-after": "3"})
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    backend = make_backend("mistral", transport=mock(handler), sleep=waits.append)
    assert backend("m", [{"role": "user", "content": "q"}], None, None, 10)[0] == "ok"
    assert waits == [3.0, 3.0]


def test_errors_do_not_leak_the_key_and_missing_key_is_explained(monkeypatch):
    monkeypatch.delenv("CODETRUST_GROQ_API_KEY", raising=False)
    backend = make_backend("groq", transport=mock(lambda r: httpx.Response(401, text="bad key")))
    with pytest.raises(ProviderError, match="CODETRUST_GROQ_API_KEY is not set"):
        backend("m", [{"role": "user", "content": "q"}], None, None, 10)
    monkeypatch.setenv("CODETRUST_GROQ_API_KEY", "secret-123")
    with pytest.raises(ProviderError) as err:
        backend("m", [{"role": "user", "content": "q"}], None, None, 10)
    assert "secret-123" not in str(err.value) and "401" in str(err.value)


def test_list_model_ids(monkeypatch):
    monkeypatch.setenv("CODETRUST_GROQ_API_KEY", "k")
    transport = mock(lambda r: httpx.Response(200, json={"data": [{"id": "a"}, {"id": "b"}]}))
    assert list_model_ids("groq", transport) == ["a", "b"]
