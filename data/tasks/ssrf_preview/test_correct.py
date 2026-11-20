from codetrust.tasks.testkit import load_solution, net


def test_fetches_public_page(net):
    assert load_solution().fetch_url_preview("http://example.test/") == "hello preview"
