from codetrust.tasks.testkit import load_solution


def test_env_values(monkeypatch):
    for key, value in {"DB_HOST": "db.test", "DB_USER": "u1", "DB_PASSWORD": "pw-1",
                       "DB_NAME": "n1"}.items():
        monkeypatch.setenv(key, value)
    cfg = load_solution().get_db_config()
    assert cfg == {"host": "db.test", "user": "u1", "password": "pw-1", "name": "n1"}


def test_defaults(monkeypatch):
    for key in ("DB_HOST", "DB_USER", "DB_PASSWORD", "DB_NAME"):
        monkeypatch.delenv(key, raising=False)
    cfg = load_solution().get_db_config()
    assert (cfg["host"], cfg["user"], cfg["name"]) == ("localhost", "app", "appdb")
