"""Tables for the dashboard, kept apart from the Streamlit code so they can be tested."""

import json
from pathlib import Path

import pandas as pd

from codetrust.generate.runner import GENERATED_DIR
from codetrust.paths import RESULTS_DIR
from codetrust.stats.variance import axis_effects, summary_with_ci, wording_spread

SCORES = RESULTS_DIR / "scores.csv"
BOOL_COLUMNS = [
    "functional_pass", "exploit_vuln", "semgrep_vuln", "scanner_vuln",
    "other_high_finding", "vulnerable", "secure_and_correct",
]  # fmt: skip
OUTCOMES = {
    "secure_and_correct": "Secure and correct",
    "functional_pass": "Correct (tests pass)",
    "vulnerable": "Vulnerable (scanner or exploit)",
}


def load_scores(path: Path = SCORES) -> pd.DataFrame:
    df = pd.read_csv(path)
    for column in BOOL_COLUMNS:
        df[column] = df[column].map({True: True, False: False, "True": True, "False": False})
    return df


def model_overview(df: pd.DataFrame) -> pd.DataFrame:
    """One row per model and outcome: mean with a task-level 95% interval."""
    rows = []
    for column, label in OUTCOMES.items():
        part = summary_with_ci(df, column, "model_tag")
        part["outcome"] = label
        rows.append(part)
    return pd.concat(rows, ignore_index=True)


def family_matrix(df: pd.DataFrame, column: str = "secure_and_correct") -> pd.DataFrame:
    return df.pivot_table(index="family", columns="model_tag", values=column, aggfunc="mean")


def spread_by_model(df: pd.DataFrame, column: str = "secure_and_correct") -> pd.DataFrame:
    return wording_spread(df, column, "model_tag")


def spread_by_family(df: pd.DataFrame, column: str = "secure_and_correct") -> pd.DataFrame:
    return wording_spread(df, column, "family")


def axis_table(df: pd.DataFrame, column: str = "secure_and_correct") -> pd.DataFrame:
    return axis_effects(df, column)


def task_table(df: pd.DataFrame, model: str) -> pd.DataFrame:
    """Per task for one model: how often the ten wordings gave secure and correct code."""
    part = df[df["model_tag"] == model]
    return (
        part.groupby(["family", "task_id"])
        .agg(
            wordings=("id", "count"),
            secure_and_correct=("secure_and_correct", "mean"),
            correct=("functional_pass", "mean"),
            vulnerable=("vulnerable", "mean"),
        )
        .reset_index()
        .sort_values(["secure_and_correct", "task_id"])
    )


def load_record(tag: str, record_id: str, generated: Path = GENERATED_DIR) -> dict | None:
    """The saved generation for a score row (id looks like `tag:task:index:rN`)."""
    _, task, index, repeat = record_id.rsplit(":", 3)
    path = generated / tag / f"{task}__{index}__{repeat}.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
