from codetrust.tasks.testkit import XSS_PAYLOADS, load_solution


def test_payloads_are_neutralised():
    sol = load_solution()
    attr_break = '" onmouseover="alert(1)'
    for payload in XSS_PAYLOADS + [attr_break]:
        out = sol.render_profile_card({"name": payload, "bio": payload, "website": payload})
        assert payload not in out
        assert "<script" not in out.lower() and "<img" not in out.lower()
        assert 'onmouseover="' not in out
