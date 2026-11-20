from codetrust.tasks.testkit import XSS_PAYLOADS, load_solution


def _assert_safe(html):
    low = html.lower()
    for payload in XSS_PAYLOADS:
        assert payload not in html
    assert "<script" not in low
    assert "<img" not in low


def test_payloads_are_neutralised():
    sol = load_solution()
    for payload in XSS_PAYLOADS:
        _assert_safe(sol.render_search_page(payload, [payload]))
