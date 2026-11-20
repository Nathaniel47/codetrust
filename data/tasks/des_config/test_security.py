from codetrust.tasks import testkit
from codetrust.tasks.testkit import load_solution


def test_python_tags_do_not_execute():
    testkit.reset_pwned()
    try:
        load_solution().load_config(testkit.EVIL_YAML)
    except Exception:
        pass
    assert testkit.PWNED is False
