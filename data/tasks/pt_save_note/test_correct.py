from pathlib import Path

from codetrust.tasks.testkit import load_solution


def test_save(tmp_path):
    path = load_solution().save_note(str(tmp_path), "todo", "buy milk")
    assert Path(path).read_text() == "buy milk"
    assert Path(path).parent == tmp_path and Path(path).name == "todo.txt"
