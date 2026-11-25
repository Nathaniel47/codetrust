import numpy as np
import pandas as pd
import pytest

from codetrust.evaluate import report
from codetrust.score.scorer import SCORE_COLUMNS


def scores(models, reminder=False, repeats=1):
    rng = np.random.default_rng(1)
    axes = ["canonical", "formal", "mentions_security"]
    tags = list(models) + ([f"{m}+reminder" for m in models] if reminder else [])
    rows = []
    for tag in tags:
        for t in range(6):
            for i, axis in enumerate(axes):
                for repeat in range(repeats):
                    good = True if "+reminder" in tag else bool(rng.integers(0, 2))
                    rows.append(
                        {
                            "id": f"{tag}:t{t}:{i}:r{repeat}", "model_tag": tag,
                            "task_id": f"t{t}", "family": "xss" if t % 2 else "ssrf",
                            "paraphrase_id": f"t{t}:{i}", "axis": axis, "repeat": repeat,
                            "extract_status": "ok", "functional_pass": True,
                            "exploit_vuln": not good, "semgrep_vuln": False,
                            "scanner_vuln": False, "other_high_finding": False,
                            "vulnerable": not good, "secure_and_correct": good,
                        }
                    )  # fmt: skip
    return pd.DataFrame(rows, columns=SCORE_COLUMNS)


OK = {"passed": 1, "failed": 0, "errors": 0}
FAIL = {"passed": 0, "failed": 1, "errors": 0}


def validation(false_alarms=1, tasks=4):
    task_rows = [
        {"id": f"t{i}", "ref_correct": OK, "ref_security": OK, "vuln_security": FAIL}
        for i in range(tasks)
    ]
    detail = [
        {"task": f"t{i}", "semgrep_caught": True, "semgrep_false_alarm": i < false_alarms}
        for i in range(tasks)
    ]
    return task_rows, {"detail": detail}


def test_scripted_rows_are_never_mixed_into_real_results():
    mixed = pd.concat([scores(["groq"]), scores(["scripted-60"])])
    used, dry = report.split_scores(mixed)
    assert not dry and set(used["model_tag"]) == {"groq"}
    used, dry = report.split_scores(scores(["scripted-60"]))
    assert dry and len(used)


def test_scorer_ceiling_counts_scanner_false_alarms():
    bounds = report.scorer_bounds(*validation(false_alarms=1, tasks=4))
    assert bounds["ceiling"] == 0.75 and bounds["ceiling_tests_only"] == 1.0
    assert bounds["floor"] == 0.0


def test_paired_difference_pairs_by_task_and_wording():
    base = scores(["m"])
    better = base.assign(secure_and_correct=True)
    result = report.paired_difference(base, better)
    assert result["effect"] == pytest.approx(1 - base["secure_and_correct"].mean())
    assert result["pairs"] == len(base) and result["ci_low"] <= result["effect"]
    assert report.paired_difference(base, better.assign(task_id="other")) is None


def test_reminder_baseline_leaves_out_the_wording_that_already_has_it():
    table = report.reminder_table(scores(["m"], reminder=True))
    assert table.iloc[0]["Prompt pairs"] == 12  # 6 tasks x 2 of the 3 wordings
    assert table.iloc[0]["Change in secure and correct"].startswith("+")
    assert report.reminder_table(scores(["m"])).empty


def test_headline_uses_one_sample_per_prompt(tmp_path):
    df = scores(["groq", "gemini"], repeats=3)
    out = report.build_report(df, *validation(), tmp_path)
    text = (out / "results.md").read_text(encoding="utf-8")
    assert "| gemini | 18 | 6 |" in text  # 18 generations, not 54


def test_real_report_has_tables_charts_and_limitations(tmp_path):
    out = report.build_report(
        scores(["groq", "gemini"], reminder=True, repeats=3), *validation(), tmp_path
    )
    assert out.name == "evaluation"
    text = (out / "results.md").read_text(encoding="utf-8")
    assert "DRY RUN" not in text and "groq minus gemini" in text
    assert "scorer" in text.lower() and "Wording versus asking again" in text
    for chart in ("by_model.png", "by_family.png", "wording_effects.png"):
        assert (out / chart).stat().st_size > 5000
    limits = (out / "limitations.md").read_text(encoding="utf-8")
    assert "would score 75%" in limits and "noise comparison rests on 6 tasks" in limits


def test_reminder_runs_stay_out_of_the_wording_tables(tmp_path):
    out = report.build_report(scores(["groq"], reminder=True), *validation(), tmp_path)
    text = (out / "results.md").read_text(encoding="utf-8")
    wording = text[text.index("## Wording sensitivity") : text.index("## By weakness type")]
    assert "groq" in wording and "+reminder" not in wording


def test_dry_run_is_labelled_and_says_what_was_not_measured(tmp_path):
    out = report.build_report(scores(["scripted-60"]), *validation(), tmp_path)
    assert out.name == "evaluation_dryrun"
    for name in ("results.md", "limitations.md"):
        assert "DRY RUN, NOT RESULTS" in (out / name).read_text(encoding="utf-8")
    text = (out / "results.md").read_text(encoding="utf-8")
    assert "_Not run yet._" in text
    limits = (out / "limitations.md").read_text(encoding="utf-8")
    assert "has not been measured" in limits and "Baseline not run" in limits
    assert not (tmp_path / "evaluation").exists()
