import numpy as np
import pandas as pd
import pytest

from codetrust.stats.agreement import agreement_table, cohens_kappa
from codetrust.stats.bootstrap import task_bootstrap_ci
from codetrust.stats.variance import (
    axis_effects,
    per_task_rates,
    resampling_noise,
    summary_with_ci,
    wording_spread,
)

AXES = ["canonical", "formal", "terse", "user_story", "verbose_context"]


def frame(outcomes: dict[str, list[int]], model="m", repeats=1):
    """outcomes: task -> list of 0/1 per wording (axis order above)."""
    rows = []
    for task, values in outcomes.items():
        for axis, value in zip(AXES, values, strict=True):
            for repeat in range(repeats):
                rows.append(
                    {
                        "model_tag": model,
                        "task_id": task,
                        "family": "f",
                        "axis": axis,
                        "paraphrase_id": f"{task}:{axis}",
                        "repeat": repeat,
                        "secure_and_correct": value,
                    }
                )
    return pd.DataFrame(rows)


def test_per_task_rates():
    df = frame({"a": [1, 1, 1, 1, 1], "b": [0, 1, 0, 1, 0]})
    rates = per_task_rates(df, "secure_and_correct").set_index("task_id")["rate"]
    assert rates["a"] == 1.0 and rates["b"] == pytest.approx(0.4)


def test_wording_spread_separates_stable_from_mixed_tasks():
    df = frame({"a": [1] * 5, "b": [0] * 5, "c": [1, 0, 1, 0, 1], "d": [1, 1, 0, 1, 1]})
    row = wording_spread(df, "secure_and_correct").iloc[0]
    assert row["tasks"] == 4 and row["share_mixed_tasks"] == 0.5
    assert row["mean"] == pytest.approx((1 + 0 + 0.6 + 0.8) / 4)
    assert 0 < row["mean_within_task_sd"] < 0.5


def test_resampling_noise_only_uses_prompts_with_repeats():
    assert resampling_noise(frame({"a": [1] * 5}), "secure_and_correct").empty
    df = frame({"a": [1] * 5}, repeats=3)
    df.loc[(df.axis == "formal") & (df.repeat == 1), "secure_and_correct"] = 0
    row = resampling_noise(df, "secure_and_correct").iloc[0]
    assert row["prompts_with_repeats"] == 5 and row["share_mixed_prompts"] == pytest.approx(0.2)


def test_bootstrap_interval_contains_mean_and_shrinks_with_more_tasks():
    rng = np.random.default_rng(0)
    small = frame({f"t{i}": list(rng.integers(0, 2, 5)) for i in range(5)})
    large = frame({f"t{i}": list(rng.integers(0, 2, 5)) for i in range(60)})
    m1, lo1, hi1 = task_bootstrap_ci(small, "secure_and_correct")
    m2, lo2, hi2 = task_bootstrap_ci(large, "secure_and_correct")
    assert lo1 <= m1 <= hi1 and lo2 <= m2 <= hi2
    assert hi2 - lo2 < hi1 - lo1


def test_bootstrap_is_seeded_and_handles_constant_and_empty_data():
    df = frame({"a": [1] * 5, "b": [1] * 5})
    assert task_bootstrap_ci(df, "secure_and_correct") == (1.0, 1.0, 1.0)
    assert task_bootstrap_ci(df, "secure_and_correct", seed=3) == task_bootstrap_ci(
        df, "secure_and_correct", seed=3
    )
    assert np.isnan(task_bootstrap_ci(df.iloc[0:0], "secure_and_correct")[0])


def test_bootstrap_ignores_missing_outcomes():
    df = frame({"a": [1] * 5, "b": [0] * 5}).astype({"secure_and_correct": float})
    df.loc[df.task_id == "b", "secure_and_correct"] = np.nan
    assert task_bootstrap_ci(df, "secure_and_correct")[0] == 1.0


def test_summary_with_ci_has_one_row_per_group():
    df = pd.concat([frame({"a": [1] * 5}, model="x"), frame({"a": [0] * 5}, model="y")])
    out = summary_with_ci(df, "secure_and_correct", "model_tag").set_index("model_tag")
    assert out.loc["x", "mean"] == 1.0 and out.loc["y", "mean"] == 0.0


def test_axis_effect_is_paired_by_task_and_signed():
    tasks = {f"t{i}": [0, 1, 0, 0, 0] for i in range(10)}  # "formal" always better than canonical
    out = axis_effects(frame(tasks), "secure_and_correct").set_index("axis")
    assert out.loc["formal", "effect"] == 1.0 and out.loc["formal", "ci_low"] == 1.0
    assert out.loc["terse", "effect"] == 0.0
    assert "canonical" not in out.index


def test_kappa_extremes():
    same = pd.Series([True, False, True, False])
    assert cohens_kappa(same, same) == 1.0
    assert cohens_kappa(same, ~same) == -1.0
    assert np.isnan(cohens_kappa(pd.Series([True, True]), pd.Series([True, True])))


def test_agreement_table_ignores_undefined_rows():
    df = pd.DataFrame(
        {
            "semgrep_vuln": [True, True, False, False],
            "other_vuln": [True, False, False, False],
            "exploit_vuln": [True, None, False, None],
        }
    )
    table = agreement_table(df, ("semgrep_vuln", "other_vuln", "exploit_vuln")).set_index(
        ["signal_a", "signal_b"]
    )
    row = table.loc[("semgrep_vuln", "exploit_vuln")]
    assert row["n"] == 2 and row["both"] == 1 and row["neither"] == 1
    assert table.loc[("semgrep_vuln", "other_vuln"), "only_a"] == 1
