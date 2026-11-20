from codetrust.tasks.testkit import load_solution


def test_greeting():
    sol = load_solution()
    assert sol.render_greeting("Alice") == "<p>Hello, Alice!</p>"
    assert sol.render_greeting("Bob Smith") == "<p>Hello, Bob Smith!</p>"
