import ast
import json

import pytest

from codetrust.config import CWE_FAMILIES, N_PARAPHRASES, N_TASKS
from codetrust.paths import DATA_DIR
from codetrust.tasks.build import build_paraphrases
from codetrust.tasks.loader import load_tasks
from codetrust.tasks.paraphrase import AXES, SECURITY_WORDS, check_paraphrases, render
from codetrust.tasks.splits import make_split
from codetrust.tasks.validate import validate_task

TASKS = load_tasks()
FILES = ("task.json", "reference.py", "vulnerable.py", "test_correct.py", "test_security.py")


def test_fifty_tasks_five_per_family():
    assert len(TASKS) == N_TASKS
    assert len({t.id for t in TASKS}) == N_TASKS
    counts = {f: sum(t.family == f for t in TASKS) for f in CWE_FAMILIES}
    assert set(counts.values()) == {5}
    assert all(t.cwe == CWE_FAMILIES[t.family] for t in TASKS)


@pytest.mark.parametrize("task", TASKS, ids=lambda t: t.id)
def test_task_files_parse_and_define_entry_points(task):
    for name in FILES:
        assert (task.path / name).exists(), name
    for name in ("reference.py", "vulnerable.py", "test_correct.py", "test_security.py"):
        ast.parse(task.read(name))
    for part in ("reference.py", "vulnerable.py"):
        defined = {n.name for n in ast.walk(ast.parse(task.read(part))) if hasattr(n, "name")}
        assert set(task.entry) <= defined, (part, task.entry)


def test_paraphrases_are_complete_and_free_of_security_hints():
    rows = build_paraphrases(TASKS)
    assert len(rows) == N_TASKS * N_PARAPHRASES
    assert check_paraphrases(TASKS, rows) == []


def test_only_the_security_axis_mentions_security():
    for task in TASKS:
        for axis in AXES:
            low = render(task, axis).lower()
            has_hint = any(w in low for w in SECURITY_WORDS)
            assert has_hint == (axis == "mentions_security"), (task.id, axis)


def test_contract_is_kept_in_every_wording_except_terse():
    for task in TASKS:
        for axis in AXES:
            if axis != "terse":
                assert task.contract_text in render(task, axis)


def test_released_files_match_the_builder():
    saved = [
        json.loads(line)
        for line in (DATA_DIR / "paraphrases.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert saved == build_paraphrases(TASKS)
    split = json.loads((DATA_DIR / "splits.json").read_text(encoding="utf-8"))
    assert split == make_split(TASKS)


def test_split_is_by_task_and_stratified():
    split = make_split(TASKS)
    assert list(split.values()).count("dev") == 20
    for family in CWE_FAMILIES:
        in_family = [split[t.id] for t in TASKS if t.family == family]
        assert in_family.count("dev") == 2 and in_family.count("test") == 3
    assert make_split(TASKS, seed=1) != split


@pytest.mark.parametrize("task_id", ["sqli_find_user", "xss_greeting", "uu_allowed_file"])
def test_validation_sample(task_id):
    task = next(t for t in TASKS if t.id == task_id)
    assert validate_task(task)["problems"] == []


@pytest.mark.slow
@pytest.mark.parametrize("task", TASKS, ids=lambda t: t.id)
def test_every_task_validates(task):
    assert validate_task(task)["problems"] == []
