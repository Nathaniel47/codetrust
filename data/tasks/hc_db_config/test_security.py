from codetrust.tasks.testkit import load_solution


def test_no_default_password(monkeypatch):
    for key in ("DB_HOST", "DB_USER", "DB_PASSWORD", "DB_NAME"):
        monkeypatch.delenv(key, raising=False)
    try:
        cfg = load_solution().get_db_config()
    except Exception:
        return
    assert not cfg.get("password")
