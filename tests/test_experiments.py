"""The pieces the Step 6 experiments depend on: seeds, subsets, reminder and complete scoring."""

import json

import pytest

from codetrust.generate import runner
from codetrust.llm.cache import ResponseCache
from codetrust.llm.client import LLMClient
from codetrust.llm.models import REMINDER, scripted_backend
from codetrust.score import run as score_run
from codetrust.score.scorer import score_model
from codetrust.tasks.loader import load_tasks


def scripted_client(tmp_path, percent=100):
    return LLMClient(
        scripted_backend(percent), "scripted", "scripted", 0.2, 1234, 1500,
        cache=ResponseCache(tmp_path / "cache"),
    )  # fmt: skip


def test_each_repeat_is_sent_with_its_own_seed(tmp_path):
    seeds = []

    def backend(model, messages, temperature, seed, max_tokens):
        seeds.append(seed)
        return "x", 1

    client = LLMClient(backend, "p", "m", 0.2, 100, cache=ResponseCache(tmp_path))
    for repeat in range(3):
        client.complete("same prompt", repeat=repeat)
    assert seeds == [100, 101, 102]


def test_records_store_the_seed_that_was_sent(tmp_path):
    client = scripted_client(tmp_path)
    runner.run(
        ["scripted"], repeats=2, task_ids={"sqli_find_user"}, out=tmp_path / "gen",
        clients={"scripted": client},
    )  # fmt: skip
    seeds = {
        json.loads(p.read_text())["repeat"]: json.loads(p.read_text())["seed"]
        for p in (tmp_path / "gen" / "scripted").glob("*.json")
    }
    assert seeds == {0: 1234, 1: 1235}


def test_noise_subset_is_one_held_out_task_per_family_and_stable():
    ids = runner.noise_task_ids()
    tasks = {t.id: t for t in load_tasks()}
    split = json.loads((runner.DATA_DIR / "splits.json").read_text(encoding="utf-8"))
    assert ids == runner.noise_task_ids()
    assert len({tasks[i].family for i in ids}) == len(ids) == 10
    assert all(split[i] == "test" for i in ids)


def test_reminder_is_added_once():
    assert runner.with_reminder("Do it.") == f"Do it.\n\n{REMINDER}"
    already = f"Do it.\n\n{REMINDER}"
    assert runner.with_reminder(already) == already


def test_reminder_generations_are_kept_apart_from_the_main_grid(tmp_path):
    out = tmp_path / "gen"
    runner.run(
        ["scripted"], task_ids={"sqli_find_user"}, out=out,
        clients={"scripted": scripted_client(tmp_path)}, reminder=True,
    )  # fmt: skip
    files = list((out / "scripted+reminder").glob("*.json"))
    assert len(files) == 10 and not (out / "scripted").exists()
    record = json.loads(files[0].read_text(encoding="utf-8"))
    assert record["model_tag"] == "scripted+reminder"
    assert record["id"].startswith("scripted+reminder:sqli_find_user:")
    assert "= ?" in record["code"]  # the scripted model answers a security request safely


def make_record(folder, stem, code="x = 1\n"):
    folder.mkdir(parents=True, exist_ok=True)
    record = {
        "id": stem, "model_tag": "m", "task_id": "t", "family": "sql_injection",
        "paraphrase_id": "t:0", "axis": "canonical", "repeat": 0,
        "extract_status": "ok" if code else "no_code", "code": code,
    }  # fmt: skip
    (folder / f"{stem}.json").write_text(json.dumps(record), encoding="utf-8")


def test_records_added_after_a_scan_are_noticed(tmp_path):
    make_record(tmp_path / "m", "old")
    scan = tmp_path / "scan.json"
    scan.write_text(json.dumps({"old": []}), encoding="utf-8")
    assert score_run.unscanned(tmp_path / "m", scan) == []
    make_record(tmp_path / "m", "new")
    make_record(tmp_path / "m", "nocode", code=None)
    assert score_run.unscanned(tmp_path / "m", scan) == ["new"]


def test_a_resumed_run_is_rescanned(tmp_path, monkeypatch):
    monkeypatch.setattr(score_run, "GENERATED_DIR", tmp_path)
    monkeypatch.setattr(score_run, "SCAN_DIR", tmp_path / "scan")
    scanned = []

    def fake_scan(code_dir):
        scanned.append(sorted(p.stem for p in code_dir.glob("*.py")))
        return {stem: [] for stem in scanned[-1]}

    monkeypatch.setattr(score_run, "scan_files", fake_scan)
    make_record(tmp_path / "m", "a")
    score_run.scan_model("m")
    score_run.scan_model("m")
    make_record(tmp_path / "m", "b")
    score_run.scan_model("m")
    assert scanned == [["a"], ["a", "b"]]


@pytest.mark.parametrize("have_tests, have_scan", [(False, True), (True, False)])
def test_scoring_refuses_incomplete_results(tmp_path, have_tests, have_scan):
    make_record(tmp_path / "gen" / "m", "a")
    results = tmp_path / "tests.jsonl"
    results.write_text(
        json.dumps({"id": "a", "ran": False}) + "\n" if have_tests else "", encoding="utf-8"
    )
    scan = tmp_path / "scan.json"
    scan.write_text(json.dumps({"a": []} if have_scan else {}), encoding="utf-8")
    with pytest.raises(ValueError, match="lack test or scan results"):
        score_model("m", tmp_path / "gen", results, scan)
