"""Test, scan and score the generations of one or more models.

    python -m codetrust.score.run --models scripted
Needs Docker (sandbox image, Semgrep image, CodeQL image). Steps already done are skipped.
"""

import argparse
import json
from pathlib import Path

import pandas as pd

from codetrust.generate.runner import GENERATED_DIR
from codetrust.paths import RESULTS_DIR
from codetrust.sandbox.runner import TEST_RESULTS_DIR, test_model
from codetrust.scan.runner import export_code, scan_files
from codetrust.score.scorer import SCORE_COLUMNS, score_model

SCAN_DIR = RESULTS_DIR / "scan"
SCORES = RESULTS_DIR / "scores.csv"


def scan_model(tag: str, scanners=("semgrep", "codeql"), rescan: bool = False) -> Path:
    out = SCAN_DIR / f"{tag}.json"
    if out.exists() and not rescan:
        return out
    code_dir = GENERATED_DIR / "_code" / tag
    export_code(GENERATED_DIR / tag, code_dir)
    SCAN_DIR.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(scan_files(code_dir, scanners)) + "\n", encoding="utf-8")
    return out


def update_scores(new_rows: list[dict], tag: str, path: Path = SCORES) -> pd.DataFrame:
    frame = pd.DataFrame(new_rows, columns=SCORE_COLUMNS)
    if path.exists():
        old = pd.read_csv(path)
        frame = pd.concat([old[old["model_tag"] != tag], frame], ignore_index=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)
    return frame


def main(argv=None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--models", required=True)
    parser.add_argument("--rescan", action="store_true")
    parser.add_argument("--scanners", default="semgrep,codeql")
    args = parser.parse_args(argv)
    for tag in args.models.split(","):
        tested = test_model(tag, GENERATED_DIR)
        scan_file = scan_model(tag, tuple(args.scanners.split(",")), args.rescan)
        rows = score_model(tag, GENERATED_DIR, TEST_RESULTS_DIR / f"{tag}.jsonl", scan_file)
        update_scores(rows, tag)
        secure = sum(r["secure_and_correct"] for r in rows)
        print(f"{tag}: {len(rows)} scored ({tested} newly tested), {secure} secure and correct")


if __name__ == "__main__":
    main()
