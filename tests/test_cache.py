from codetrust.llm.cache import ResponseCache, cache_key

MSG = [{"role": "user", "content": "hi"}]


def test_key_changes_with_every_input():
    base = cache_key("groq", "m", MSG, 0.2, 1)
    assert base == cache_key("groq", "m", MSG, 0.2, 1)
    assert base != cache_key("gemini", "m", MSG, 0.2, 1)
    assert base != cache_key("groq", "m", MSG, 0.3, 1)
    assert base != cache_key("groq", "m", MSG, 0.2, 2)
    assert base != cache_key("groq", "m", MSG, 0.2, 1, repeat=1)


def test_roundtrip(tmp_path):
    cache = ResponseCache(tmp_path)
    assert cache.get("k") is None
    cache.put("k", "code")
    assert cache.get("k") == "code"
