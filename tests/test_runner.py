from codetrust.tasks.loader import Task
from codetrust.tasks.runner import run_tests


def make_task(tmp_path, test_code):
    (tmp_path / "test_x.py").write_text(test_code, encoding="utf-8")
    return Task("t", "f", "CWE-0", "r", "s", [], [], tmp_path)


def test_pass_fail_and_error_are_told_apart(tmp_path):
    code = "from codetrust.tasks.testkit import load_solution\n"
    ok = make_task(tmp_path, code + "def test_a():\n    assert load_solution().x == 1\n")
    assert run_tests(ok, "test_x.py", "x = 1\n").ok
    assert run_tests(ok, "test_x.py", "x = 2\n").failed == 1
    assert (
        run_tests(ok, "test_x.py", "def broken(:\n").errors
        + run_tests(ok, "test_x.py", "def broken(:\n").failed
        > 0
    )


def test_timeout(tmp_path):
    task = make_task(tmp_path, "def test_a():\n    import time\n    time.sleep(5)\n")
    assert run_tests(task, "test_x.py", "", timeout=1).timed_out
