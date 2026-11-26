"""The single entry point for LLM calls: cache first, then budget, then a pluggable backend."""

from collections.abc import Callable

from codetrust.llm.budget import TokenBudget, estimate_tokens
from codetrust.llm.cache import ResponseCache, cache_key

# backend(model, messages, temperature, seed, max_tokens) -> (text, tokens_used)
Backend = Callable[[str, list[dict], float | None, int | None, int], tuple[str, int]]


class LLMClient:
    def __init__(
        self,
        backend: Backend,
        provider: str,
        model: str,
        temperature: float | None,
        seed: int | None,
        max_tokens: int = 1500,
        cache: ResponseCache | None = None,
        budget: TokenBudget | None = None,
        params: dict | None = None,
    ):
        self.backend = backend
        self.provider = provider
        self.model = model
        self.temperature = temperature
        self.seed = seed
        self.max_tokens = max_tokens
        self.params = params or {}  # model-specific settings the backend sends
        self.cache = cache or ResponseCache()
        self.budget = budget
        self.calls = 0
        self.cache_hits = 0
        self.tokens_used = 0

    def complete(self, prompt: str, system: str | None = None, repeat: int = 0) -> str:
        """Each repeat gets its own cache entry and its own seed (`seed + repeat`): with one fixed
        seed a provider may return the same text every time, hiding the sampling noise."""
        messages = ([{"role": "system", "content": system}] if system else []) + [
            {"role": "user", "content": prompt}
        ]
        key = cache_key(
            self.provider,
            self.model,
            messages,
            self.temperature,
            self.seed,
            repeat,
            self.max_tokens,
            self.params,
        )
        hit = self.cache.get(key)
        if hit is not None:
            self.cache_hits += 1
            return hit
        estimate = estimate_tokens((system or "") + prompt) + self.max_tokens // 2
        if self.budget:
            self.budget.before_call(estimate)
        seed = None if self.seed is None else self.seed + repeat
        text, tokens = self.backend(self.model, messages, self.temperature, seed, self.max_tokens)
        tokens = tokens or estimate
        if self.budget:
            self.budget.record(tokens)
        self.calls += 1
        self.tokens_used += tokens
        self.cache.put(key, text)
        return text
