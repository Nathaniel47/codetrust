"""Runs inside the sandbox container: test every listed generation, print one JSON line each.

Input: a text file with one generation record path per line (mounted read-only). The container has
no network, a read-only root, no capabilities and a non-root user (see sandbox/runner.py).
"""

import argparse
import json
import sys
from pathlib import Path

from codetrust.tasks.loader import load_tasks
from codetrust.tasks.runner import run_tests

PER_TEST_TIMEOUT = 90


def outcome_dict(outcome) -> dict:
    return {
        "passed": outcome.passed,
        "failed": outcome.failed,
        "errors": outcome.errors,
        "timed_out": outcome.timed_out,
    }


def test_record(record: dict, tasks: dict) -> dict:
    result = {"id": record["id"], "task_id": record["task_id"]}
    code = record.get("code")
    if not code:
        return {**result, "ran": False, "reason": record.get("extract_status", "no_code")}
    task = tasks[record["task_id"]]
    return {
        **result,
        "ran": True,
        "correct": outcome_dict(run_tests(task, "test_correct.py", code, PER_TEST_TIMEOUT)),
        "security": outcome_dict(run_tests(task, "test_security.py", code, PER_TEST_TIMEOUT)),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--list", required=True)
    parser.add_argument("--tasks-dir", default=None)
    args = parser.parse_args(argv)
    tasks = {
        t.id: t for t in (load_tasks(Path(args.tasks_dir)) if args.tasks_dir else load_tasks())
    }
    for line in Path(args.list).read_text(encoding="utf-8").split():
        record = json.loads(Path(line).read_text(encoding="utf-8"))
        print(json.dumps(test_record(record, tasks)), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
