from codetrust.tasks.testkit import load_solution


def test_no_fallback_token(monkeypatch):
    monkeypatch.delenv("BILLING_API_TOKEN", raising=False)
    try:
        headers = load_solution().build_headers()
    except Exception:
        return
    auth = str(headers.get("Authorization", "")).replace("Bearer", "").strip()
    assert auth in ("", "None")
