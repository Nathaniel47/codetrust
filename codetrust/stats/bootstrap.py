"""Confidence intervals that respect the data's structure.

The ten wordings of one task are not independent samples (they share the task), so the bootstrap
resamples whole tasks, not individual generations.
"""

import numpy as np
import pandas as pd

from codetrust.config import SEED


def task_bootstrap_ci(
    df: pd.DataFrame,
    column: str,
    n_boot: int = 2000,
    seed: int = SEED,
    level: float = 0.95,
) -> tuple[float, float, float]:
    """Mean of a 0/1 column with a task-level percentile bootstrap interval: (mean, low, high)."""
    values = df.dropna(subset=[column]).copy()
    values[column] = values[column].astype(float)
    sums = values.groupby("task_id")[column].agg(["sum", "count"])
    if sums.empty:
        return float("nan"), float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    totals, counts = sums["sum"].to_numpy(), sums["count"].to_numpy()
    picks = rng.integers(0, len(sums), size=(n_boot, len(sums)))
    means = totals[picks].sum(axis=1) / counts[picks].sum(axis=1)
    tail = (1 - level) / 2
    return (
        float(totals.sum() / counts.sum()),
        float(np.quantile(means, tail)),
        float(np.quantile(means, 1 - tail)),
    )
