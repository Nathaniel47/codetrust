import json

from codetrust.llm.meta import update_run_meta


def test_run_meta_records_fields_and_commit(tmp_path):
    path = tmp_path / "run_meta.json"
    update_run_meta(path, temperature=0.2, seed=1234)
    meta = update_run_meta(path, models=["a"])
    on_disk = json.loads(path.read_text(encoding="utf-8"))
    assert on_disk == meta
    assert meta["temperature"] == 0.2 and meta["seed"] == 1234 and meta["models"] == ["a"]
    assert "git_commit" in meta
