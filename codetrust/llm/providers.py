"""HTTP backends for the two providers. Plain httpx, no vendor SDKs.

Keys come only from CODETRUST_* environment variables and are sent in headers, never in URLs or
error messages.
"""

import os
import time

import httpx

from codetrust.config import PROVIDER_KEY_VARS

OPENAI_COMPATIBLE = {
    "groq": "https://api.groq.com/openai/v1",
}
GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta"


class ProviderError(RuntimeError):
    pass


def api_key(provider: str) -> str:
    var = PROVIDER_KEY_VARS[provider]
    key = os.environ.get(var, "")
    if not key:
        raise ProviderError(f"{var} is not set")
    return key


def _post(url, headers, payload, transport, sleep, retries=6) -> dict:
    with httpx.Client(transport=transport, timeout=120) as http:
        for attempt in range(retries):
            try:
                resp = http.post(url, headers=headers, json=payload)
            except httpx.TransportError as exc:
                if attempt == retries - 1:
                    raise ProviderError(
                        f"network error ({type(exc).__name__}); resume later (answers are cached)"
                    ) from exc
                sleep(min(60, 5 * 2**attempt))
                continue
            if resp.status_code == 429 or resp.status_code >= 500:
                wait = resp.headers.get("retry-after", "")
                sleep(min(90, float(wait)) if wait.isdigit() else min(60, 5 * 2**attempt))
                continue
            if resp.status_code != 200:
                raise ProviderError(f"HTTP {resp.status_code}: {resp.text[:200]}")
            return resp.json()
    raise ProviderError("provider keeps answering 429/5xx; resume later (answers are cached)")


def openai_compatible_backend(provider: str, transport=None, sleep=time.sleep, params=None):
    base = OPENAI_COMPATIBLE[provider]

    def backend(model, messages, temperature, seed, max_tokens):
        payload = {"model": model, "messages": messages, "max_tokens": max_tokens}
        payload.update(params or {})
        if temperature is not None:
            payload["temperature"] = temperature
        if seed is not None:
            payload["seed"] = seed
        headers = {"Authorization": f"Bearer {api_key(provider)}"}
        data = _post(f"{base}/chat/completions", headers, payload, transport, sleep)
        text = data["choices"][0]["message"].get("content") or ""
        return text, int((data.get("usage") or {}).get("total_tokens", 0))

    return backend


def gemini_backend(transport=None, sleep=time.sleep):
    def backend(model, messages, temperature, seed, max_tokens):
        system = [m["content"] for m in messages if m["role"] == "system"]
        contents = [
            {"role": "user" if m["role"] == "user" else "model", "parts": [{"text": m["content"]}]}
            for m in messages
            if m["role"] != "system"
        ]
        config = {"maxOutputTokens": max_tokens}
        if temperature is not None:
            config["temperature"] = temperature
        if seed is not None:
            config["seed"] = seed
        payload = {"contents": contents, "generationConfig": config}
        if system:
            payload["systemInstruction"] = {"parts": [{"text": "\n".join(system)}]}
        headers = {"x-goog-api-key": api_key("gemini")}
        data = _post(
            f"{GEMINI_BASE}/models/{model}:generateContent", headers, payload, transport, sleep
        )
        candidates = data.get("candidates") or []
        parts = candidates[0].get("content", {}).get("parts", []) if candidates else []
        text = "".join(p.get("text", "") for p in parts)
        return text, int((data.get("usageMetadata") or {}).get("totalTokenCount", 0))

    return backend


def make_backend(provider: str, transport=None, sleep=time.sleep, params=None):
    if provider == "gemini":
        return gemini_backend(transport, sleep)
    if provider in OPENAI_COMPATIBLE:
        return openai_compatible_backend(provider, transport, sleep, params)
    raise ValueError(f"unknown provider {provider}")


def list_model_ids(provider: str, transport=None) -> list[str]:
    """Names the provider currently offers (used to check the configured model ID exists)."""
    with httpx.Client(transport=transport, timeout=60) as http:
        if provider == "gemini":
            resp = http.get(f"{GEMINI_BASE}/models", headers={"x-goog-api-key": api_key(provider)})
            resp.raise_for_status()
            return [m["name"].removeprefix("models/") for m in resp.json().get("models", [])]
        resp = http.get(
            f"{OPENAI_COMPATIBLE[provider]}/models",
            headers={"Authorization": f"Bearer {api_key(provider)}"},
        )
        resp.raise_for_status()
        return [m["id"] for m in resp.json().get("data", [])]
