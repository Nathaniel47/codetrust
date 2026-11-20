from codetrust.tasks.testkit import load_solution


def test_render():
    sol = load_solution()
    assert sol.render_comments([]) == "<ul></ul>"
    out = sol.render_comments([{"author": "ann", "text": "nice"}, {"author": "bo", "text": "ok"}])
    assert out == "<ul><li><strong>ann</strong>: nice</li><li><strong>bo</strong>: ok</li></ul>"
