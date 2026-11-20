"""How good are the scanners on code whose answer we know?

Scans every task's safe reference solution and deliberately vulnerable solution, and reports, per
scanner and family, how many vulnerable solutions are caught (recall) and how many safe ones are
wrongly flagged (false positives). These numbers are what limits the scanner part of the score.

    python -m codetrust.scan.validate [--scanners semgrep,codeql]
"""

import argparse
import json
from collections import defaultdict

from codetrust.generate.runner import GENERATED_DIR
from codetrust.paths import RESULTS_DIR
from codetrust.scan.runner import scan_files
from codetrust.score.scorer import in_family
from codetrust.tasks.loader import load_tasks


def export_solutions(tasks, code_dir):
    code_dir.mkdir(parents=True, exist_ok=True)
    for task in tasks:
        for kind in ("reference", "vulnerable"):
            (code_dir / f"{task.id}__{kind}.py").write_text(
                task.read(f"{kind}.py"), encoding="utf-8"
            )


def evaluate(tasks, scans: dict[str, list[dict]], scanners) -> dict:
    """Per scanner and family: caught vulnerable, flagged reference; plus per-task detail."""
    table: dict = {
        s: defaultdict(lambda: {"tasks": 0, "caught": 0, "false_alarm": 0}) for s in scanners
    }
    detail = []
    for task in tasks:
        row = {"task": task.id, "family": task.family}
        for scanner in scanners:
            caught = in_family(scans[f"{task.id}__vulnerable"], task.family, scanner)
            alarm = in_family(scans[f"{task.id}__reference"], task.family, scanner)
            cell = table[scanner][task.family]
            cell["tasks"] += 1
            cell["caught"] += caught
            cell["false_alarm"] += alarm
            row[f"{scanner}_caught"], row[f"{scanner}_false_alarm"] = caught, alarm
        detail.append(row)
    return {"by_family": {s: dict(t) for s, t in table.items()}, "detail": detail}


def render(result: dict, scanners) -> str:
    lines = ["# Scanner validation", "",
             "Each task's vulnerable solution should be flagged and its safe reference should not "
             "be. A finding counts only if its CWE belongs to the task's family.", ""]  # fmt: skip
    for scanner in scanners:
        cells = result["by_family"][scanner]
        total = {k: sum(c[k] for c in cells.values()) for k in ("tasks", "caught", "false_alarm")}
        lines += [
            f"## {scanner}", "",
            f"Caught {total['caught']} of {total['tasks']} vulnerable solutions; "
            f"{total['false_alarm']} of {total['tasks']} safe solutions wrongly flagged.", "",
            "| Family | Tasks | Caught | False alarms |", "|---|---|---|---|",
        ]  # fmt: skip
        for family, c in sorted(cells.items()):
            lines.append(f"| {family} | {c['tasks']} | {c['caught']} | {c['false_alarm']} |")
        lines.append("")
    misses = [d for d in result["detail"] if not any(d[f"{s}_caught"] for s in scanners)]
    lines += ["## Vulnerable solutions that no scanner caught", ""]
    lines += [f"- `{d['task']}` ({d['family']})" for d in misses] or ["None."]
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--scanners", default="semgrep,codeql")
    scanners = tuple(parser.parse_args(argv).scanners.split(","))
    tasks = load_tasks()
    code_dir = GENERATED_DIR / "_code" / "solutions"
    export_solutions(tasks, code_dir)
    scans = scan_files(code_dir, scanners)
    result = evaluate(tasks, scans, scanners)
    RESULTS_DIR.mkdir(exist_ok=True)
    (RESULTS_DIR / "scanner_validation.json").write_text(
        json.dumps({"scans": scans, **result}, indent=1) + "\n", encoding="utf-8"
    )
    (RESULTS_DIR / "scanner_validation.md").write_text(render(result, scanners), encoding="utf-8")
    print(render(result, scanners))


if __name__ == "__main__":
    main()
