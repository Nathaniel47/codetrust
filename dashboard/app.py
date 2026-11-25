import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import altair as alt  # noqa: E402
import streamlit as st  # noqa: E402

from codetrust import dashboard_data as dd  # noqa: E402
from codetrust.stats.agreement import agreement_table  # noqa: E402
from codetrust.stats.variance import resampling_noise  # noqa: E402

st.set_page_config(page_title="CodeTrust", layout="wide")
st.title("CodeTrust")
st.caption(
    "How secure and correct is AI-generated web-app code, and how much does it change when the "
    "same request is worded differently? Every generation is scored automatically: unit tests, "
    "an exploit-style security test and Semgrep. No model judges another model."
)

if not dd.SCORES.exists():
    st.warning(
        "No results yet. Generate and score code first:\n\n"
        "`python -m codetrust.generate.runner --models scripted`\n\n"
        "`python -m codetrust.score.run --models scripted`"
    )
    st.stop()

scores = dd.load_scores(dd.SCORES)
models = sorted(scores["model_tag"].unique())
if any(m.startswith("scripted") for m in models):
    st.info("Models named `scripted*` are offline test doubles, not real model results.")

picked = st.sidebar.multiselect("Models", models, default=models)
scores = scores[scores["model_tag"].isin(picked)]
st.sidebar.write(
    f"{len(scores):,} generations, {scores['task_id'].nunique()} tasks, "
    f"{scores['family'].nunique()} vulnerability families"
)
if scores.empty:
    st.stop()

overview, by_family, by_wording, by_task, agreement = st.tabs(
    ["Per model", "Per vulnerability type", "Wording effect", "Task drill-down", "Scanners"]
)

with overview:
    table = dd.model_overview(scores)
    chart = alt.Chart(table).encode(
        y=alt.Y("model_tag:N", title=None),
        color=alt.Color("outcome:N", title=None),
        yOffset="outcome:N",
    )
    st.altair_chart(
        chart.mark_bar().encode(
            x=alt.X("mean:Q", title="Share of generations", scale=alt.Scale(domain=[0, 1]))
        )
        + chart.mark_rule().encode(x="ci_low:Q", x2="ci_high:Q"),
        use_container_width=True,
    )
    st.caption("Bars show the mean; lines show a 95% interval that resamples whole tasks.")
    st.dataframe(table.round(3), hide_index=True)

with by_family:
    matrix = dd.family_matrix(scores)
    long = matrix.reset_index().melt("family", var_name="model", value_name="secure_and_correct")
    st.altair_chart(
        alt.Chart(long)
        .mark_rect()
        .encode(
            x=alt.X("model:N", title=None),
            y=alt.Y("family:N", title=None),
            color=alt.Color("secure_and_correct:Q", scale=alt.Scale(domain=[0, 1])),
            tooltip=["model", "family", alt.Tooltip("secure_and_correct:Q", format=".2f")],
        ),
        use_container_width=True,
    )
    st.subheader("How much the wording changes the outcome, per family")
    st.dataframe(dd.spread_by_family(scores).round(3), hide_index=True)

with by_wording:
    st.write(
        "For each task the same request is worded 10 ways. **Share of mixed tasks** is the share "
        "of tasks where some wordings give secure and correct code and others do not."
    )
    st.dataframe(dd.spread_by_model(scores).round(3), hide_index=True)
    noise = resampling_noise(scores, "secure_and_correct")
    if noise.empty:
        st.caption(
            "No repeated samples of the same prompt yet, so wording effects cannot be separated "
            "from plain randomness. Run the generator with `--repeats 3` on a subset."
        )
    else:
        st.write("Baseline: how often the *same* prompt gives different outcomes on repeats.")
        st.dataframe(noise.round(3), hide_index=True)
    effects = dd.axis_table(scores)
    if not effects.empty:
        st.subheader("Effect of each wording compared with the canonical one")
        base = alt.Chart(effects).encode(y=alt.Y("axis:N", title=None), color="model_tag:N")
        st.altair_chart(
            base.mark_point(filled=True).encode(
                x=alt.X("effect:Q", title="Change in secure-and-correct share")
            )
            + base.mark_rule().encode(x="ci_low:Q", x2="ci_high:Q"),
            use_container_width=True,
        )

with by_task:
    model = st.selectbox("Model", picked)
    tasks = dd.task_table(scores, model)
    st.dataframe(tasks.round(2), hide_index=True)
    task_id = st.selectbox("Task", tasks["task_id"])
    rows = scores[(scores["model_tag"] == model) & (scores["task_id"] == task_id)]
    rows = rows.sort_values(["paraphrase_id", "repeat"])
    chosen = st.selectbox("Generation", rows["id"])
    record = dd.load_record(model, chosen)
    row = rows[rows["id"] == chosen].iloc[0]
    st.write(
        f"Wording: **{row['axis']}** · correct: **{row['functional_pass']}** · exploitable: "
        f"**{row['exploit_vuln']}** · Semgrep: **{row['semgrep_vuln']}**"
    )
    if record:
        st.code(record["code"] or record["reply"], language="python")
    else:
        st.caption("Generated code is not available in this deployment.")

with agreement:
    st.write(
        "Do the signals agree? Kappa is 1 for perfect agreement and 0 for chance level. "
        "`exploit_vuln` is only defined for functionally correct code."
    )
    st.dataframe(agreement_table(scores).round(3), hide_index=True)
