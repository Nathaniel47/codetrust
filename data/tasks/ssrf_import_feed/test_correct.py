from codetrust.tasks.testkit import load_solution, net


def test_titles(net):
    assert load_solution().import_feed("http://example.test/feed") == ["First", "Second"]
