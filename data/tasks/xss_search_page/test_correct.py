from codetrust.tasks.testkit import load_solution


def test_page():
    out = load_solution().render_search_page("python", ["Intro", "Advanced"])
    assert 'Results for "python"' in out.replace("&quot;", '"')
    assert "<li>Intro</li>" in out and "<li>Advanced</li>" in out
