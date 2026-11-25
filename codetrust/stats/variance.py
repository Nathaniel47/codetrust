"""How much does the outcome change when the same task is worded differently?

All functions take the score table (one row per generation) and the name of a boolean outcome
column, usually `secure_and_correct`.
"""

import numpy as np
import pandas as pd

from codetrust.config import SEED
from codetrust.stats.bootstrap import task_bootstrap_ci


def _clean(df: pd.DataFrame, column: str) -> pd.DataFrame:
    out = df.dropna(subset=[column]).copy()
    out[column] = out[column].astype(float)
    return out


def per_task_rates(df: pd.DataFrame, column: str) -> pd.DataFrame:
    """Share of wordings (and repeats) with a positive outcome, for each model and task."""
    values = _clean(df, column)
    grouped = values.groupby(["model_tag", "family", "task_id"])[column]
    return grouped.agg(rate="mean", n="count").reset_index()


def wording_spread(df: pd.DataFrame, column: str, group: str = "model_tag") -> pd.DataFrame:
    """Per group: mean outcome, the mean within-task SD across wordings, and how many tasks give
    a different outcome for different wordings ("mixed" tasks)."""
    rates = per_task_rates(df, column)
    rows = []
    for key, part in rates.groupby(group):
        sd = np.sqrt(part["rate"] * (1 - part["rate"]))  # SD of a 0/1 outcome with that mean
        rows.append(
            {
                group: key,
                "tasks": len(part),
                "mean": part["rate"].mean(),
                "mean_within_task_sd": sd.mean(),
                "share_mixed_tasks": ((part["rate"] > 0) & (part["rate"] < 1)).mean(),
            }
        )
    return pd.DataFrame(rows)


def main_grid(df: pd.DataFrame) -> pd.DataFrame:
    """One sample per prompt. Headline numbers use only this, so repeated tasks are not
    counted several times."""
    return df[df["repeat"] == 0]


def _disagreement_between_repeats(successes: float, n: int) -> float:
    """Chance that two different samples of the same prompt have different outcomes."""
    return 2 * successes * (n - successes) / (n * (n - 1))


def wording_vs_noise(
    df: pd.DataFrame, column: str, n_boot: int = 2000, seed: int = SEED
) -> pd.DataFrame:
    """Does changing the wording change the outcome more than asking again does?

    Both numbers are the chance that TWO single answers disagree, so they are comparable however
    many wordings or repeats there are. `same_prompt` takes two samples of one prompt;
    `across_wordings` takes one sample each of two different wordings of the task. `excess` is the
    difference (task-bootstrap 95% interval): clearly above zero means wording matters beyond
    sampling noise. Uses only prompts with at least two repeats.
    """
    values = _clean(df, column)
    prompts = values.groupby(["model_tag", "task_id", "paraphrase_id"])[column].agg(
        ["sum", "count"]
    )
    prompts = prompts[prompts["count"] >= 2]
    rng = np.random.default_rng(seed)
    rows = []
    for model, part in prompts.groupby(level="model_tag"):
        same, cross = [], []
        for _, task in part.groupby(level="task_id"):
            k, n = task["sum"].to_numpy(), task["count"].to_numpy()
            if len(task) < 2:
                continue
            pairs_of_counts = zip(k, n, strict=True)
            same.append(np.mean([_disagreement_between_repeats(a, b) for a, b in pairs_of_counts]))
            p = k / n
            pairs = [
                p[i] * (1 - p[j]) + p[j] * (1 - p[i])
                for i in range(len(p))
                for j in range(i + 1, len(p))
            ]
            cross.append(np.mean(pairs))
        if not same:
            continue
        diff = np.array(cross) - np.array(same)
        boots = diff[rng.integers(0, len(diff), size=(n_boot, len(diff)))].mean(axis=1)
        rows.append(
            {
                "model_tag": model,
                "tasks": len(diff),
                "same_prompt": float(np.mean(same)),
                "across_wordings": float(np.mean(cross)),
                "excess": float(diff.mean()),
                "ci_low": float(np.quantile(boots, 0.025)),
                "ci_high": float(np.quantile(boots, 0.975)),
            }
        )
    columns = [
        "model_tag", "tasks", "same_prompt", "across_wordings", "excess", "ci_low", "ci_high",
    ]  # fmt: skip
    return pd.DataFrame(rows, columns=columns)


def summary_with_ci(df: pd.DataFrame, column: str, group: str, seed: int = SEED) -> pd.DataFrame:
    """Mean outcome per group with a task-level bootstrap 95% interval."""
    rows = []
    for key, part in df.groupby(group):
        mean, low, high = task_bootstrap_ci(part, column, seed=seed)
        rows.append({group: key, "n": int(part[column].notna().sum()), "mean": mean,
                     "ci_low": low, "ci_high": high})  # fmt: skip
    return pd.DataFrame(rows)


def axis_effects(
    df: pd.DataFrame,
    column: str,
    baseline: str = "canonical",
    n_boot: int = 2000,
    seed: int = SEED,
    level: float = 0.95,
) -> pd.DataFrame:
    """Per model and wording axis: change in the outcome compared with the baseline wording.

    The difference is paired by task (same task, different wording), and the interval comes from
    resampling tasks.
    """
    values = _clean(df, column)
    rng = np.random.default_rng(seed)
    rows = []
    for model, part in values.groupby("model_tag"):
        per = part.groupby(["task_id", "axis"])[column].mean().unstack("axis")
        if baseline not in per:
            continue
        for axis in per.columns:
            if axis == baseline:
                continue
            diff = (per[axis] - per[baseline]).dropna().to_numpy()
            if len(diff) == 0:
                continue
            boots = diff[rng.integers(0, len(diff), size=(n_boot, len(diff)))].mean(axis=1)
            rows.append(
                {
                    "model_tag": model,
                    "axis": axis,
                    "effect": diff.mean(),
                    "ci_low": float(np.quantile(boots, (1 - level) / 2)),
                    "ci_high": float(np.quantile(boots, 1 - (1 - level) / 2)),
                    "tasks": len(diff),
                }
            )
    return pd.DataFrame(rows, columns=["model_tag", "axis", "effect", "ci_low", "ci_high", "tasks"])
