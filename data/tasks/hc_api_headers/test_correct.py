from codetrust.tasks.testkit import load_solution


def test_headers(monkeypatch):
    monkeypatch.setenv("BILLING_API_TOKEN", "tok-123")
    assert load_solution().build_headers() == {
        "Authorization": "Bearer tok-123",
        "Accept": "application/json",
    }
