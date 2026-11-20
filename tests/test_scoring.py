import json

import pandas as pd

from codetrust.scan.normalise import codeql_findings, cwe_numbers, is_high, semgrep_findings
from codetrust.score.run import update_scores
from codetrust.score.scorer import (
    in_family,
    score_model,
    score_record,
)
from codetrust.score.scorer import (
    tests_pass as outcome_passes,
)

OK = {"passed": 2, "failed": 0, "errors": 0, "timed_out": False}
BAD = {"passed": 0, "failed": 1, "errors": 0, "timed_out": False}
RECORD = {
    "id": "m:t:0:r0", "model_tag": "m", "task_id": "t", "family": "sql_injection",
    "paraphrase_id": "t:0", "axis": "canonical", "repeat": 0, "extract_status": "ok",
}  # fmt: skip


def finding(scanner="semgrep", cwe=(89,), severity="error"):
    return {"scanner": scanner, "file": "x.py", "rule": "r", "cwe": list(cwe),
            "severity": severity, "line": 1}  # fmt: skip


def make_tests(correct=OK, security=OK):
    return {"ran": True, "correct": correct, "security": security}


def test_cwe_numbers_from_both_scanners_formats():
    assert cwe_numbers(["CWE-89: SQL Injection"]) == [89]
    assert cwe_numbers(["external/cwe/cwe-089", "security", "external/cwe/cwe-564"]) == [89, 564]
    assert cwe_numbers(None) == []


def test_semgrep_json_is_normalised():
    data = {
        "results": [
            {
                "check_id": "rules.codetrust.weak-hash",
                "path": "/src/a__0__r0.py",
                "start": {"line": 7},
                "extra": {"severity": "WARNING", "metadata": {"cwe": ["CWE-327: Broken"]}},
            }
        ]
    }
    assert semgrep_findings(data) == [
        {"scanner": "semgrep", "file": "a__0__r0.py", "rule": "weak-hash", "cwe": [327],
         "severity": "warning", "line": 7}
    ]  # fmt: skip


def test_sarif_is_normalised_with_severity_from_score():
    sarif = {
        "runs": [
            {
                "tool": {"driver": {"rules": [
                    {"id": "py/sql-injection",
                     "properties": {"tags": ["external/cwe/cwe-089"], "security-severity": "8.8"}}
                ]}},
                "results": [{
                    "ruleId": "py/sql-injection",
                    "locations": [{"physicalLocation": {
                        "artifactLocation": {"uri": "a.py"}, "region": {"startLine": 3}}}],
                }],
            }
        ]
    }  # fmt: skip
    (f,) = codeql_findings(sarif)
    assert (f["cwe"], f["severity"], f["file"], f["line"]) == ([89], "high", "a.py", 3)
    assert is_high(f)


def test_family_scope_decides_what_counts():
    assert in_family([finding(cwe=(89,))], "sql_injection")
    assert not in_family([finding(cwe=(79,))], "sql_injection")
    assert in_family([finding("codeql")], "sql_injection", "codeql")
    assert not in_family([finding("codeql")], "sql_injection", "semgrep")


def test_outcome_passes_needs_at_least_one_passing_test_and_no_trouble():
    assert outcome_passes(OK)
    assert not outcome_passes(BAD)
    assert not outcome_passes({**OK, "errors": 1})
    assert not outcome_passes({**OK, "timed_out": True})
    assert not outcome_passes({**OK, "passed": 0})
    assert not outcome_passes(None)


def test_secure_and_correct_needs_all_three_signals_clean():
    row = score_record(RECORD, make_tests(), [])
    assert row["functional_pass"] and row["exploit_vuln"] is False
    assert row["secure_and_correct"] and not row["vulnerable"]


def test_failed_security_test_means_exploitable():
    row = score_record(RECORD, make_tests(security=BAD), [])
    assert row["exploit_vuln"] and row["vulnerable"] and not row["secure_and_correct"]


def test_scanner_finding_alone_makes_it_vulnerable():
    row = score_record(RECORD, make_tests(), [finding("codeql")])
    assert row["codeql_vuln"] and not row["semgrep_vuln"] and row["scanner_vuln"]
    assert row["vulnerable"] and not row["secure_and_correct"]


def test_exploit_result_is_unknown_when_code_is_not_functional():
    row = score_record(RECORD, make_tests(correct=BAD, security=BAD), [])
    assert row["exploit_vuln"] is None and not row["functional_pass"]
    assert not row["secure_and_correct"]


def test_code_that_was_not_run_is_a_functional_failure():
    row = score_record(RECORD, {"ran": False, "reason": "no_code"}, [])
    assert not row["functional_pass"] and row["exploit_vuln"] is None
    assert not score_record(RECORD, None, [])["functional_pass"]


def test_out_of_family_high_findings_are_reported_separately():
    row = score_record(RECORD, make_tests(), [finding(cwe=(79,), severity="error")])
    assert row["other_high_finding"] and not row["scanner_vuln"] and row["secure_and_correct"]


def test_score_model_joins_records_tests_and_scans(tmp_path):
    gen = tmp_path / "gen" / "m"
    gen.mkdir(parents=True)
    (gen / "t__0__r0.json").write_text(json.dumps(RECORD), encoding="utf-8")
    results = tmp_path / "tests.jsonl"
    results.write_text(json.dumps({"id": RECORD["id"], **make_tests()}) + "\n", encoding="utf-8")
    scan = tmp_path / "scan.json"
    scan.write_text(json.dumps({"t__0__r0": [finding()]}), encoding="utf-8")
    (row,) = score_model("m", tmp_path / "gen", results, scan)
    assert row["vulnerable"] and row["functional_pass"]


def test_update_scores_replaces_only_that_models_rows(tmp_path):
    path = tmp_path / "scores.csv"
    row_a = score_record({**RECORD, "model_tag": "a"}, make_tests(), [])
    row_b = score_record({**RECORD, "model_tag": "b"}, make_tests(), [])
    update_scores([row_a], "a", path)
    update_scores([row_b], "b", path)
    frame = update_scores([{**row_a, "secure_and_correct": False}], "a", path)
    assert sorted(frame["model_tag"]) == ["a", "b"]
    assert not frame[frame.model_tag == "a"].secure_and_correct.iloc[0]
    assert isinstance(pd.read_csv(path), pd.DataFrame)
