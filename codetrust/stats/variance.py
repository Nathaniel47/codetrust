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


def resampling_noise(df: pd.DataFrame, column: str) -> pd.DataFrame:
    """Baseline: how often does the SAME prompt give different outcomes on repeated sampling?

    Only prompts with at least two repeats are used. Compare `share_mixed_prompts` with
    `wording_spread().share_mixed_tasks`: wording only matters beyond plain randomness if tasks
    are mixed across wordings clearly more often than prompts are mixed across repeats.
    """
    values = _clean(df, column)
    per_prompt = values.groupby(["model_tag", "paraphrase_id"])[column].agg(["mean", "count"])
    per_prompt = per_prompt[per_prompt["count"] >= 2].reset_index()
    rows = []
    for tag, part in per_prompt.groupby("model_tag"):
        rows.append(
            {
                "model_tag": tag,
                "prompts_with_repeats": len(part),
                "share_mixed_prompts": ((part["mean"] > 0) & (part["mean"] < 1)).mean(),
            }
        )
    return pd.DataFrame(rows, columns=["model_tag", "prompts_with_repeats", "share_mixed_prompts"])


def summary_with_ci(df: pd.DataFrame, column: str, group: str, seed: int = SEED) -> pd.DataFrame:
    """Mean outcome per group with a task-level bootstrap 95% interval."""
    rows = []
    for key, part in df.groupby(group):
        mean, low, high = task_bootstrap_ci(part, column, seed=seed)
        rows.append({group: key, "n": int(part[column].notna().sum()), "mean": mean,
                     "ci_low": low, "ci_high": high})  # fmt: skip
    return pd.DataFrame(rows)


def axis_effects(
    df: pd.DataFrame, column: str, baseline: str = "canonical", n_boot: int = 2000, seed: int = SEED
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
                    "ci_low": float(np.quantile(boots, 0.025)),
                    "ci_high": float(np.quantile(boots, 0.975)),
                    "tasks": len(diff),
                }
            )
    return pd.DataFrame(rows, columns=["model_tag", "axis", "effect", "ci_low", "ci_high", "tasks"])
