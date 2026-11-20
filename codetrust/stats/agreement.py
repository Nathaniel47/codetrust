"""How much do the scoring signals agree with each other?"""

import pandas as pd


def cohens_kappa(a: pd.Series, b: pd.Series) -> float:
    """Agreement between two yes/no signals beyond chance (1 = perfect, 0 = chance level)."""
    both = pd.concat([a, b], axis=1).dropna().astype(bool)
    if both.empty:
        return float("nan")
    x, y = both.iloc[:, 0], both.iloc[:, 1]
    observed = (x == y).mean()
    expected = x.mean() * y.mean() + (1 - x.mean()) * (1 - y.mean())
    return float("nan") if expected == 1 else float((observed - expected) / (1 - expected))


def agreement_table(
    df: pd.DataFrame, signals=("semgrep_vuln", "codeql_vuln", "exploit_vuln")
) -> pd.DataFrame:
    """Pairwise kappa and counts. exploit_vuln is only defined for functionally correct code."""
    rows = []
    for i, first in enumerate(signals):
        for second in signals[i + 1 :]:
            pair = df[[first, second]].dropna().astype(bool)
            rows.append(
                {
                    "signal_a": first,
                    "signal_b": second,
                    "n": len(pair),
                    "both": int((pair[first] & pair[second]).sum()),
                    "only_a": int((pair[first] & ~pair[second]).sum()),
                    "only_b": int((~pair[first] & pair[second]).sum()),
                    "neither": int((~pair[first] & ~pair[second]).sum()),
                    "kappa": cohens_kappa(pair[first], pair[second]),
                }
            )
    return pd.DataFrame(rows)
