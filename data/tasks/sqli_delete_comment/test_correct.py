from codetrust.tasks.testkit import db, load_solution


def test_delete_own(db):
    sol = load_solution()
    assert sol.delete_comment(db, 1, "bob") == 1
    assert db.execute("SELECT COUNT(*) FROM comments").fetchone()[0] == 2


def test_not_author(db):
    assert load_solution().delete_comment(db, 2, "bob") == 0
    assert db.execute("SELECT COUNT(*) FROM comments").fetchone()[0] == 3
