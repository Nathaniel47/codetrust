from codetrust.tasks.testkit import db, load_solution


def test_search(db):
    sol = load_solution()
    assert sol.search_products(db, "mug") == ["Blue Mug", "Red Mug"]
    assert sol.search_products(db, "LAMP") == ["Desk Lamp"]
    assert sol.search_products(db, "zzz") == []
