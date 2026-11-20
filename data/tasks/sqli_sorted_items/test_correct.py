from codetrust.tasks.testkit import db, load_solution


def test_sorting(db):
    sol = load_solution()
    assert sol.list_items(db, "name") == ["Alpha", "Mid", "Zeta"]
    assert sol.list_items(db, "price") == ["Mid", "Zeta", "Alpha"]
    assert sol.list_items(db, "id") == ["Zeta", "Alpha", "Mid"]
    assert sol.list_items(db, "bogus") == ["Zeta", "Alpha", "Mid"]
