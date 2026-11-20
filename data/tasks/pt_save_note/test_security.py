from codetrust.tasks.testkit import load_solution


def test_no_escape(tmp_path):
    base = tmp_path / "notes"
    base.mkdir()
    before = {p for p in tmp_path.rglob("*")}
    sol = load_solution()
    for title in ["../evil", "../../evil", "sub/../../evil"]:
        try:
            sol.save_note(str(base), title, "x")
        except Exception:
            pass
    created = {p for p in tmp_path.rglob("*")} - before
    assert all(base in p.parents or p == base for p in created)
