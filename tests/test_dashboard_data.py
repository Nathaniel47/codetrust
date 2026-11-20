import json

import pandas as pd

from codetrust import dashboard_data as dd
from codetrust.score.scorer import SCORE_COLUMNS


def scores_frame():
    rows = []
    for model, rate in (("a", 1), ("b", 0)):
        for task, family in (("t1", "xss"), ("t2", "ssrf")):
            for i in range(10):
                good = bool(rate) if task == "t1" else i % 2 == 0
                rows.append(
                    {
                        "id": f"{model}:{task}:{i}:r0", "model_tag": model, "task_id": task,
                        "family": family, "paraphrase_id": f"{task}:{i}",
                        "axis": ["canonical", "formal"][i % 2], "repeat": 0,
                        "extract_status": "ok", "functional_pass": True, "exploit_vuln": not good,
                        "semgrep_vuln": False, "codeql_vuln": False, "scanner_vuln": False,
                        "other_high_finding": False, "vulnerable": not good,
                        "secure_and_correct": good,
                    }
                )  # fmt: skip
    return pd.DataFrame(rows, columns=SCORE_COLUMNS)


def test_scores_roundtrip_through_csv_with_missing_exploit_values(tmp_path):
    df = scores_frame().astype({"exploit_vuln": object})
    df.loc[0, "exploit_vuln"] = None
    df.to_csv(tmp_path / "s.csv", index=False)
    loaded = dd.load_scores(tmp_path / "s.csv")
    assert loaded["secure_and_correct"].dtype == bool
    assert pd.isna(loaded.loc[0, "exploit_vuln"])


def test_overview_has_every_model_and_outcome():
    out = dd.model_overview(scores_frame())
    assert set(out["model_tag"]) == {"a", "b"} and set(out["outcome"]) == set(dd.OUTCOMES.values())
    top = out[(out.model_tag == "a") & (out.outcome == "Secure and correct")].iloc[0]
    assert top["mean"] == 0.75 and top["ci_low"] <= top["mean"] <= top["ci_high"]


def test_family_matrix_and_spread():
    df = scores_frame()
    matrix = dd.family_matrix(df)
    assert matrix.loc["xss", "a"] == 1.0 and matrix.loc["xss", "b"] == 0.0
    spread = dd.spread_by_model(df).set_index("model_tag")
    assert spread.loc["a", "share_mixed_tasks"] == 0.5
    assert set(dd.spread_by_family(df)["family"]) == {"xss", "ssrf"}


def test_task_table_sorts_worst_first():
    table = dd.task_table(scores_frame(), "a")
    assert list(table["task_id"]) == ["t2", "t1"]


def test_load_record_finds_the_saved_generation(tmp_path):
    folder = tmp_path / "m"
    folder.mkdir()
    (folder / "sqli_find_user__3__r0.json").write_text(json.dumps({"code": "x"}), encoding="utf-8")
    assert dd.load_record("m", "m:sqli_find_user:3:r0", tmp_path) == {"code": "x"}
    assert dd.load_record("m", "m:other:1:r0", tmp_path) is None
