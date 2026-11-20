from codetrust.tasks import testkit
from codetrust.tasks.testkit import load_solution


def test_parse():
    cfg = load_solution().load_config("name: demo\nports: [80, 443]\ndebug: false\n")
    assert cfg == {"name": "demo", "ports": [80, 443], "debug": False}
