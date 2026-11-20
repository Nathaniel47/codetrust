from codetrust.tasks import testkit
from codetrust.tasks.testkit import load_solution


def test_malicious_file_does_not_execute(tmp_path):
    testkit.reset_pwned()
    path = tmp_path / "evil.cache"
    path.write_bytes(testkit.evil_pickle())
    try:
        load_solution().load_cache_entry(str(path))
    except Exception:
        pass
    assert testkit.PWNED is False
