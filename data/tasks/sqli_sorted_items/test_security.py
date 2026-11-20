from codetrust.tasks.testkit import db, load_solution


def test_unknown_column_not_interpreted(db):
    sol = load_solution()
    by_id = ["Zeta", "Alpha", "Mid"]
    for payload in ["price DESC", "name DESC", "(CASE WHEN 1 THEN price END) DESC"]:
        assert sol.list_items(db, payload) == by_id
