from codetrust.tasks.testkit import db, load_solution


def test_filter(db):
    sol = load_solution()
    assert sol.get_orders(db, 1, "paid") == [1]
    assert sol.get_orders(db, 2, "shipped") == [4]
    assert sol.get_orders(db, 3, "paid") == []
