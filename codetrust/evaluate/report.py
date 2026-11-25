"""Step 6: turn the score table into the results tables, charts and limitations.

    python -m codetrust.evaluate.report

Real model results go to results/evaluation/. If the score table only holds the offline
`scripted*` test models, everything goes to results/evaluation_dryrun/ and is labelled as a dry run:
those numbers test this code and say nothing about any model.
"""

import argparse
import json
from itertools import combinations
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from codetrust.config import SEED  # noqa: E402
from codetrust.dashboard_data import SCORES, load_scores  # noqa: E402
from codetrust.llm.meta import update_run_meta  # noqa: E402
from codetrust.llm.models import REMINDER_SUFFIX  # noqa: E402
from codetrust.paths import RESULTS_DIR  # noqa: E402
from codetrust.stats.agreement import agreement_table  # noqa: E402
from codetrust.stats.bootstrap import task_bootstrap_ci  # noqa: E402
from codetrust.stats.variance import (  # noqa: E402
    axis_effects,
    main_grid,
    wording_spread,
    wording_vs_noise,
)

DRY_RUN_BANNER = (
    "> **DRY RUN, NOT RESULTS.** These numbers come from the offline `scripted` test model, which "
    "hands out this project's own safe or flawed solutions at a fixed rate. They check that the "
    "evaluation code works and say nothing about any real model.\n"
)
HEADLINE = "secure_and_correct"
# Validated colour-blind-safe pair (dataviz reference palette, slots 1 and 2), then grey.
MODEL_COLOURS = ["#2a78d6", "#eb6834", "#1baf7a"]
INK, MUTED, GRID, SURFACE = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"


def split_scores(scores: pd.DataFrame) -> tuple[pd.DataFrame, bool]:
    """Real models only if there are any; otherwise the scripted rows, flagged as a dry run."""
    scripted = scores["model_tag"].str.startswith("scripted")
    return (scores[~scripted], False) if (~scripted).any() else (scores, True)


def base_models(df: pd.DataFrame) -> list[str]:
    return sorted(m for m in df["model_tag"].unique() if not m.endswith(REMINDER_SUFFIX))


def interval(df: pd.DataFrame, column: str) -> str:
    mean, low, high = task_bootstrap_ci(df, column)
    return "n/a" if np.isnan(mean) else f"{mean:.0%} ({low:.0%} to {high:.0%})"


def headline_table(main: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for model, part in main.groupby("model_tag"):
        rows.append(
            {
                "Model": model,
                "Generations": len(part),
                "Tasks": part["task_id"].nunique(),
                "No usable code": int((part["extract_status"] != "ok").sum()),
                "Correct": interval(part, "functional_pass"),
                "Vulnerable": interval(part, "vulnerable"),
                "Secure and correct": interval(part, HEADLINE),
            }
        )
    return pd.DataFrame(rows)


def scoring_sensitivity(main: pd.DataFrame) -> pd.DataFrame:
    """How much does the headline depend on trusting the scanner?"""
    work = main.copy()
    work["tests_only"] = work["functional_pass"].astype(bool) & work["exploit_vuln"].eq(False)
    return pd.DataFrame(
        [
            {
                "Model": model,
                "Tests only": interval(part, "tests_only"),
                "Tests and Semgrep (headline)": interval(part, HEADLINE),
            }
            for model, part in work.groupby("model_tag")
        ]
    )


def scorer_bounds(task_validation: list[dict], scanner_validation: dict) -> dict:
    """What a perfect model (always the reference solution) and a worst one would score."""
    detail = {d["task"]: d for d in scanner_validation["detail"]}
    ceiling, floor = [], []
    for row in task_validation:
        flags = detail[row["id"]]
        ref_ok = all(
            row[k]["failed"] + row[k]["errors"] == 0 for k in ("ref_correct", "ref_security")
        )
        caught = row["vuln_security"]["failed"] > 0 or flags["semgrep_caught"]
        ceiling.append(ref_ok and not flags["semgrep_false_alarm"])
        floor.append(not caught)
    return {
        "tasks": len(ceiling),
        "ceiling": float(np.mean(ceiling)),
        "floor": float(np.mean(floor)),
        "ceiling_tests_only": float(
            np.mean(
                [
                    r["ref_correct"]["failed"] + r["ref_security"]["failed"] == 0
                    for r in task_validation
                ]
            )
        ),  # fmt: skip
    }


def paired_difference(
    first: pd.DataFrame, second: pd.DataFrame, column: str = HEADLINE, n_boot: int = 2000
) -> dict | None:
    """second minus first, paired by (task, wording); the interval resamples tasks."""
    keys = ["task_id", "axis"]
    joined = first[keys + [column]].merge(second[keys + [column]], on=keys, suffixes=("_a", "_b"))
    if joined.empty:
        return None
    joined["diff"] = joined[f"{column}_b"].astype(float) - joined[f"{column}_a"].astype(float)
    sums = joined.groupby("task_id")["diff"].agg(["sum", "count"])
    totals, counts = sums["sum"].to_numpy(), sums["count"].to_numpy()
    picks = np.random.default_rng(SEED).integers(0, len(sums), size=(n_boot, len(sums)))
    boots = totals[picks].sum(axis=1) / counts[picks].sum(axis=1)
    return {
        "effect": float(totals.sum() / counts.sum()),
        "ci_low": float(np.quantile(boots, 0.025)),
        "ci_high": float(np.quantile(boots, 0.975)),
        "tasks": len(sums),
        "pairs": len(joined),
    }


def signed(result: dict) -> str:
    return (
        f"{result['effect'] * 100:+.0f} points "
        f"({result['ci_low'] * 100:+.0f} to {result['ci_high'] * 100:+.0f})"
    )


def reminder_table(main: pd.DataFrame) -> pd.DataFrame:
    """The baseline mitigation: the same prompts with one security sentence added."""
    rows = []
    for model in base_models(main):
        # The `mentions_security` wording already contains the sentence, so it is left out.
        plain = main[(main["model_tag"] == model) & (main["axis"] != "mentions_security")]
        added = main[
            (main["model_tag"] == model + REMINDER_SUFFIX) & (main["axis"] != "mentions_security")
        ]
        result = paired_difference(plain, added)
        if result:
            rows.append(
                {
                    "Model": model,
                    "Prompt pairs": result["pairs"],
                    "Tasks": result["tasks"],
                    "Change in secure and correct": signed(result),
                }
            )
    return pd.DataFrame(rows)


def model_comparison(main: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for a, b in combinations(base_models(main), 2):
        result = paired_difference(main[main["model_tag"] == a], main[main["model_tag"] == b])
        if result:
            rows.append({"Comparison": f"{b} minus {a}", "Tasks": result["tasks"],
                         "Difference": signed(result)})  # fmt: skip
    return pd.DataFrame(rows)


def wording_effects(main: pd.DataFrame) -> pd.DataFrame:
    """Each wording against the canonical one. Many comparisons are made at once, so each effect
    also gets a stricter (Bonferroni) interval; only those that still exclude zero are marked."""
    plain = axis_effects(main, HEADLINE)
    if plain.empty:
        return plain.assign(survives_correction=[])
    strict = axis_effects(main, HEADLINE, n_boot=20000, level=1 - 0.05 / len(plain))
    plain["survives_correction"] = (strict["ci_low"] > 0) | (strict["ci_high"] < 0)
    return plain


def markdown(df: pd.DataFrame) -> str:
    if df.empty:
        return "_Not run yet._"
    head = "| " + " | ".join(map(str, df.columns)) + " |"
    rule = "|" + "---|" * len(df.columns)
    body = ["| " + " | ".join(map(str, row)) + " |" for row in df.itertuples(index=False)]
    return "\n".join([head, rule, *body])


# ----------------------------------------------------------------------------------- charts


def _style(ax):
    ax.set_facecolor(SURFACE)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
    ax.tick_params(colors=MUTED, length=0)


def _save(fig, path: Path, title: str, dry_run: bool):
    fig.suptitle(("DRY RUN (test model): " if dry_run else "") + title, color=INK, fontsize=11)
    fig.tight_layout()
    fig.savefig(path, dpi=150, facecolor=SURFACE)
    plt.close(fig)


def chart_by_model(main: pd.DataFrame, ceiling: float, path: Path, dry_run: bool):
    models = base_models(main)
    fig, ax = plt.subplots(figsize=(7, 1.4 + 0.7 * len(models)), facecolor=SURFACE)
    for i, model in enumerate(models):
        mean, low, high = task_bootstrap_ci(main[main["model_tag"] == model], HEADLINE)
        ax.barh(i, mean, height=0.5, color=MODEL_COLOURS[0])
        ax.errorbar(mean, i, xerr=[[mean - low], [high - mean]], color=INK, capsize=3, lw=1.2)
        ax.text(min(high + 0.02, 0.97), i, f"{mean:.0%}", va="center", color=INK, fontsize=9)
    ax.axvline(ceiling, color=MUTED, ls="--", lw=1)
    ax.text(ceiling, -0.55, f"scorer ceiling {ceiling:.0%} ", ha="right", color=MUTED, fontsize=8)
    ax.set_yticks(range(len(models)), models)
    ax.set_xlim(0, 1)
    ax.set_ylim(len(models) - 0.5, -0.75)
    ax.xaxis.set_major_formatter(lambda x, _: f"{x:.0%}")
    _style(ax)
    _save(fig, path, "Secure and correct code, with 95% intervals", dry_run)


def chart_by_family(main: pd.DataFrame, path: Path, dry_run: bool):
    models = base_models(main)
    table = main[main["model_tag"].isin(models)].pivot_table(
        index="family", columns="model_tag", values=HEADLINE, aggfunc="mean"
    )
    values = table.to_numpy(dtype=float)
    fig, ax = plt.subplots(figsize=(max(7.0, 4.5 + 1.2 * len(models)), 5), facecolor=SURFACE)
    ax.imshow(values, cmap="Blues", vmin=0, vmax=1, aspect="auto")
    for row in range(values.shape[0]):
        for col in range(values.shape[1]):
            colour = "white" if values[row, col] > 0.55 else INK
            ax.text(col, row, f"{values[row, col]:.0%}", ha="center", va="center",
                    color=colour, fontsize=9)  # fmt: skip
    ax.set_xticks(range(len(table.columns)), table.columns)
    ax.set_yticks(range(len(table.index)), [f.replace("_", " ") for f in table.index])
    _style(ax)
    _save(fig, path, "Secure and correct by weakness type (5 tasks each)", dry_run)


def chart_wording(effects: pd.DataFrame, path: Path, dry_run: bool):
    effects = effects[effects["model_tag"].map(lambda m: not m.endswith(REMINDER_SUFFIX))]
    models = sorted(effects["model_tag"].unique())
    axes = sorted(effects["axis"].unique())
    fig, ax = plt.subplots(figsize=(7.5, 5), facecolor=SURFACE)
    for i, model in enumerate(models):
        part = effects[effects["model_tag"] == model].set_index("axis").reindex(axes)
        y = np.arange(len(axes)) + (i - (len(models) - 1) / 2) * 0.22
        ax.errorbar(
            part["effect"], y,
            xerr=[part["effect"] - part["ci_low"], part["ci_high"] - part["effect"]],
            fmt="o", ms=6, lw=2, color=MODEL_COLOURS[i % len(MODEL_COLOURS)], label=model,
        )  # fmt: skip
    ax.axvline(0, color=MUTED, lw=1)
    ax.set_yticks(range(len(axes)), [a.replace("_", " ") for a in axes])
    ax.invert_yaxis()
    ax.xaxis.set_major_formatter(lambda x, _: f"{x * 100:+.0f}")
    ax.set_xlabel("change in secure-and-correct share vs canonical wording (points)", color=MUTED)
    if len(models) > 1:
        ax.legend(frameon=False, labelcolor=INK)
    _style(ax)
    _save(fig, path, "Effect of each wording, with 95% intervals", dry_run)


# ----------------------------------------------------------------------------------- report


def limitations(
    main: pd.DataFrame, noise: pd.DataFrame, reminder: pd.DataFrame, bounds: dict
) -> str:
    models = base_models(main)
    noise_text = (
        "**Wording versus randomness has not been measured**: no prompt was sampled more than "
        "once, so wording differences cannot yet be told apart from chance."
        if noise.empty
        else f"**The noise comparison rests on {int(noise['tasks'].min())} tasks** with repeated "
        "samples, so its interval is wide and a small wording effect could be missed."
    )
    items = [
        f"**Small benchmark.** {main['task_id'].nunique()} tasks, 5 per weakness type. Per-type "
        "numbers can move 20 points on one task; read them as hints, not rankings.",
        f"**Few models.** {len(models)} model(s) in this report ({', '.join(models)}). Nothing "
        "here supports claims about LLMs in general.",
        f"**The scorer is not perfect.** A model that always returned the reference solution would "
        f"score {bounds['ceiling']:.0%}, not 100%, because Semgrep wrongly flags some safe code. "
        "Compare models with that ceiling, and with the tests-only column.",
        '**"Secure" means only: the attacks we wrote did not work and Semgrep found nothing.** '
        "Semgrep catches none of the missing-permission-check flaws; there the exploit test is the "
        "only signal.",
        "**Tests checked against two solutions each** (one safe, one flawed). An unusual but safe "
        "solution could fail, and an unusual flaw could pass. No sample of model output has been "
        "checked by hand.",
        "**Prompts give hints.** Tests need exact names, so some prompts reveal environment "
        "variable names, header names or allowed hosts. Models probably look safer than they "
        "would with open requests.",
        "**Wordings are templates** around one unchanged specification. They measure sensitivity "
        "to framing, tone and typos, not to genuinely different explanations of a requirement.",
        "**Narrow scope.** Python only, mostly single functions, no surrounding codebase.",
        noise_text,
        "**Many comparisons.** With nine wordings per model some 95% intervals will exclude zero "
        "by chance; trust only effects marked as surviving the correction.",
        "**One author** wrote the tasks, tests and Semgrep rules, so their blind spots coincide.",
        "**Moving targets.** Seeds are best effort at the providers, free models are renamed or "
        "updated, and the Semgrep image is not pinned. Versions are recorded in run_meta.json and "
        "raw answers are cached locally.",
    ]
    if reminder.empty:
        items.append("**Baseline not run**: the security-reminder condition has no data yet.")
    improvements = [
        "More tasks per weakness type, including some written by other people.",
        "Hand-check about 100 model generations to estimate how often the scorer is wrong.",
        "Hand-written paraphrases, and open-ended prompts that give fewer hints.",
        "More repeated samples on more tasks, to narrow the noise interval.",
        "More models, after reading their terms.",
    ]
    return "\n".join(
        ["# Limitations", ""]
        + [f"{i}. {text}" for i, text in enumerate(items, 1)]
        + ["", "## What would improve the results", ""]
        + [f"- {text}" for text in improvements]
    ) + "\n"  # fmt: skip


def build_report(
    scores: pd.DataFrame, task_validation: list[dict], scanner_validation: dict, out_root: Path
) -> Path:
    used, dry_run = split_scores(scores)
    out = out_root / ("evaluation_dryrun" if dry_run else "evaluation")
    out.mkdir(parents=True, exist_ok=True)
    main = main_grid(used)
    base = main[main["model_tag"].isin(base_models(main))]
    bounds = scorer_bounds(task_validation, scanner_validation)
    spread = wording_spread(base, HEADLINE)
    noise = wording_vs_noise(used[used["model_tag"].isin(base_models(main))], HEADLINE)
    effects = wording_effects(base)
    reminder = reminder_table(main)

    family = base.pivot_table(index="family", columns="model_tag", values=HEADLINE, aggfunc="mean")
    family = family.map(lambda v: f"{v:.0%}").reset_index()
    effect_view = pd.DataFrame(
        {
            "Model": effects["model_tag"],
            "Wording": effects["axis"],
            "Change vs canonical": [signed(r) for r in effects.to_dict("records")],
            "Survives correction": np.where(effects["survives_correction"], "yes", "no"),
        }
    )
    noise_view = noise.copy()
    for column in ("same_prompt", "across_wordings", "excess", "ci_low", "ci_high"):
        noise_view[column] = noise_view[column].map(lambda v: f"{v:.3f}")

    sections = ["# Evaluation results", ""]
    if dry_run:
        sections.append(DRY_RUN_BANNER)
    sections += [
        "Intervals are 95% and resample whole tasks (seeded). Headline tables use one sample per "
        "prompt.",
        "## Headline", markdown(headline_table(base)), "![By model](by_model.png)",
        "## Scorer bounds (baseline)",
        f"On the {bounds['tasks']} tasks, always returning the safe reference solution would "
        f"score **{bounds['ceiling']:.0%}** secure and correct "
        f"({bounds['ceiling_tests_only']:.0%} on tests alone); always returning the flawed "
        f"solution would score **{bounds['floor']:.0%}**.",
        "## Does the headline depend on the scanner?", markdown(scoring_sensitivity(base)),
        "## Baseline mitigation: add a one-line security reminder", markdown(reminder),
        "## Model comparison (paired by task and wording)", markdown(model_comparison(main)),
        "## Wording sensitivity", markdown(spread.round(3)),
        "`share_mixed_tasks` also counts plain randomness. The next table separates the two.",
        "### Wording versus asking again", markdown(noise_view),
        "`excess` is how much more often two different wordings disagree than two samples of the "
        "same prompt. It shows a wording effect only if its interval is above zero.",
        "### Effect of each wording", markdown(effect_view), "![Wording](wording_effects.png)",
        "## By weakness type", markdown(family), "![By weakness type](by_family.png)",
        "## Do the signals agree?", markdown(agreement_table(base).round(2)),
        "See [limitations.md](limitations.md).",
    ]  # fmt: skip
    (out / "results.md").write_text("\n\n".join(sections) + "\n", encoding="utf-8")
    (out / "limitations.md").write_text(
        (DRY_RUN_BANNER + "\n" if dry_run else "") + limitations(main, noise, reminder, bounds),
        encoding="utf-8",
    )
    chart_by_model(main, bounds["ceiling"], out / "by_model.png", dry_run)
    chart_by_family(main, out / "by_family.png", dry_run)
    if not effects.empty:
        chart_wording(effects, out / "wording_effects.png", dry_run)
    return out


def main(argv=None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scores", type=Path, default=SCORES)
    args = parser.parse_args(argv)

    def read(name):
        return json.loads((RESULTS_DIR / name).read_text(encoding="utf-8"))

    scores = load_scores(args.scores)
    out = build_report(
        scores, read("task_validation.json"), read("scanner_validation.json"), RESULTS_DIR
    )
    update_run_meta(
        evaluation={
            "bootstrap_seed": SEED,
            "models": sorted(split_scores(scores)[0]["model_tag"].unique()),
            "output": out.name,
        }
    )
    print(f"written to {out}")


if __name__ == "__main__":
    main()
