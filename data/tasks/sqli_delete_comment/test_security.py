from codetrust.tasks.testkit import db, load_solution


def test_injection_deletes_nothing(db):
    sol = load_solution()
    for payload in ["x' OR '1'='1", "nobody' OR id > 0 --"]:
        assert sol.delete_comment(db, 1, payload) == 0
    assert db.execute("SELECT COUNT(*) FROM comments").fetchone()[0] == 3
