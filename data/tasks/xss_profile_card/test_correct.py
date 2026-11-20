from codetrust.tasks.testkit import load_solution


def test_card():
    user = {"name": "Ann", "bio": "Loves tea", "website": "https://ann.example.test/"}
    out = load_solution().render_profile_card(user)
    assert out == (
        '<div class="card"><h2>Ann</h2><p>Loves tea</p>'
        '<a href="https://ann.example.test/">Website</a></div>'
    )
