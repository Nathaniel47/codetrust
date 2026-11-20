import json
from pathlib import Path

import pytest

from codetrust.sandbox import driver
from codetrust.sandbox.runner import container_path, docker_command
from codetrust.scan import runner as scan_runner
from codetrust.scan.validate import evaluate, render
from codetrust.tasks.loader import load_tasks

TASKS = {t.id: t for t in load_tasks()}


def test_sandbox_container_is_locked_down(tmp_path):
    cmd = docker_command(tmp_path, tmp_path / "list.txt")
    joined = " ".join(cmd)
    for flag in ("--network none", "--read-only", "--cap-drop ALL",
                 "--security-opt no-new-privileges", "--user 1000:1000"):  # fmt: skip
        assert flag in joined
    mounts = [cmd[i + 1] for i, a in enumerate(cmd) if a == "-v"]
    assert len(mounts) == 3 and all(m.endswith(":ro") for m in mounts)
    assert "--privileged" not in joined


def test_container_paths_are_posix(tmp_path):
    path = tmp_path / "sub" / "a.json"
    assert container_path(path, tmp_path) == "/in/sub/a.json"


def test_driver_reports_tests_for_good_and_bad_code():
    task = TASKS["sqli_find_user"]
    base = {"id": "r", "task_id": task.id}
    good = driver.test_record({**base, "code": task.read("reference.py")}, TASKS)
    assert good["correct"]["failed"] == 0 and good["security"]["failed"] == 0
    bad = driver.test_record({**base, "code": task.read("vulnerable.py")}, TASKS)
    assert bad["correct"]["failed"] == 0 and bad["security"]["failed"] == 1
    broken = driver.test_record({**base, "code": "def find_user(:\n"}, TASKS)
    assert broken["correct"]["errors"] + broken["correct"]["failed"] > 0


def test_driver_skips_records_without_code():
    row = driver.test_record(
        {"id": "r", "task_id": "x", "code": None, "extract_status": "no_code"}, TASKS
    )
    assert row == {"id": "r", "task_id": "x", "ran": False, "reason": "no_code"}


def test_scanner_containers_have_no_network_and_read_only_code(tmp_path):
    semgrep = " ".join(scan_runner.semgrep_command(tmp_path))
    assert "--network none" in semgrep and f"{tmp_path}:/src:ro" in semgrep
    assert "SEMGREP_SEND_METRICS=off" in semgrep
    codeql = " ".join(scan_runner.codeql_command(tmp_path))
    assert "--network none" in codeql and f"{tmp_path}:/src:ro" in codeql
    assert "--tmpfs /work" in codeql


def test_export_code_writes_one_file_per_record_with_code(tmp_path):
    records = tmp_path / "m"
    records.mkdir()
    (records / "a__0__r0.json").write_text(json.dumps({"code": "x = 1\n"}), encoding="utf-8")
    (records / "b__0__r0.json").write_text(json.dumps({"code": None}), encoding="utf-8")
    assert scan_runner.export_code(records, tmp_path / "code") == 1
    assert (tmp_path / "code" / "a__0__r0.py").read_text() == "x = 1\n"


def test_scan_files_assigns_findings_to_files_and_keeps_clean_ones(tmp_path, monkeypatch):
    (tmp_path / "a.py").write_text("x = 1\n")
    (tmp_path / "b.py").write_text("y = 2\n")
    hit = {"scanner": "semgrep", "file": "a.py", "rule": "r", "cwe": [89],
           "severity": "error", "line": 1}  # fmt: skip
    monkeypatch.setattr(scan_runner, "run_semgrep", lambda d: [hit])
    monkeypatch.setattr(scan_runner, "run_codeql", lambda d: [])
    assert scan_runner.scan_files(tmp_path) == {"a": [hit], "b": []}


def test_scanner_validation_counts_catches_and_false_alarms():
    tasks = [TASKS["sqli_find_user"], TASKS["xss_greeting"]]
    sql = {"scanner": "semgrep", "cwe": [89], "severity": "error"}
    scans = {
        "sqli_find_user__vulnerable": [sql],
        "sqli_find_user__reference": [],
        "xss_greeting__vulnerable": [],
        "xss_greeting__reference": [{"scanner": "semgrep", "cwe": [79], "severity": "error"}],
    }
    result = evaluate(tasks, scans, ("semgrep",))
    by = result["by_family"]["semgrep"]
    assert by["sql_injection"] == {"tasks": 1, "caught": 1, "false_alarm": 0}
    assert by["xss"] == {"tasks": 1, "caught": 0, "false_alarm": 1}
    text = render(result, ("semgrep",))
    assert "Caught 1 of 2" in text and "`xss_greeting`" in text


@pytest.mark.docker
def test_real_sandbox_runs_generated_code_without_network(tmp_path):
    from codetrust.sandbox.runner import test_model

    gen = tmp_path / "gen" / "m"
    gen.mkdir(parents=True)
    task = TASKS["ssrf_preview"]
    for kind in ("reference", "vulnerable"):
        record = {"id": kind, "task_id": task.id, "code": task.read(f"{kind}.py"),
                  "extract_status": "ok"}  # fmt: skip
        (gen / f"{kind}.json").write_text(json.dumps(record), encoding="utf-8")
    assert test_model("m", tmp_path / "gen", tmp_path / "out", shards=1, batch=2) == 2
    rows = {
        r["id"]: r
        for r in map(json.loads, (tmp_path / "out" / "m.jsonl").read_text().split("\n")[:-1])
    }
    assert rows["reference"]["security"]["failed"] == 0
    assert rows["vulnerable"]["security"]["failed"] == 1


@pytest.mark.docker
def test_real_semgrep_flags_the_vulnerable_sql_solution(tmp_path):
    task = TASKS["sqli_find_user"]
    (tmp_path / "vuln.py").write_text(task.read("vulnerable.py"), encoding="utf-8")
    (tmp_path / "safe.py").write_text(task.read("reference.py"), encoding="utf-8")
    result = scan_runner.scan_files(Path(tmp_path), ("semgrep",))
    assert any(89 in f["cwe"] for f in result["vuln"])
    assert result["safe"] == []
