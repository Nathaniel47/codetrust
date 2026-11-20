from codetrust.tasks.testkit import load_solution, net


def test_reachable(net):
    sol = load_solution()
    assert sol.webhook_is_reachable("http://example.test/") is True
    assert sol.webhook_is_reachable("http://example.test/missing") is False
