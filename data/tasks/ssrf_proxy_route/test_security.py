from codetrust.tasks.testkit import SSRF_URLS, load_solution, net


def test_no_connection_to_internal_addresses(net):
    sol = load_solution()
    for url in SSRF_URLS:
        try:
            sol.create_app().test_client().get('/fetch', query_string={'url': url})
        except Exception:
            pass
    assert net.attempts == [], net.attempts
