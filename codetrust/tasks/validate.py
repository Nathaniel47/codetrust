"""Check that every task's tests mean what they should.

For each task: the reference solution must pass the correctness tests and the security tests, and
the deliberately vulnerable solution must pass the correctness tests but fail the security tests.
If the vulnerable one passes the security tests, the security test is too weak to detect anything.
"""

import json
from concurrent.futures import ThreadPoolExecutor

from codetrust.paths import RESULTS_DIR
from codetrust.tasks.loader import Task, load_tasks
from codetrust.tasks.runner import run_tests


def validate_task(task: Task) -> dict:
    ref, vuln = task.read("reference.py"), task.read("vulnerable.py")
    result = {
        "id": task.id,
        "family": task.family,
        "ref_correct": run_tests(task, "test_correct.py", ref),
        "ref_security": run_tests(task, "test_security.py", ref),
        "vuln_correct": run_tests(task, "test_correct.py", vuln),
        "vuln_security": run_tests(task, "test_security.py", vuln),
    }
    problems = []
    if not result["ref_correct"].ok:
        problems.append("reference fails correctness tests")
    if not result["ref_security"].ok:
        problems.append("reference fails security tests")
    if not result["vuln_correct"].ok:
        problems.append("vulnerable solution fails correctness tests")
    if result["vuln_security"].ok:
        problems.append("vulnerable solution passes security tests (test cannot detect the flaw)")
    result["problems"] = problems
    return result


def validate_all(tasks: list[Task] | None = None, workers: int = 4) -> list[dict]:
    tasks = tasks if tasks is not None else load_tasks()
    with ThreadPoolExecutor(workers) as pool:
        return list(pool.map(validate_task, tasks))


def to_jsonable(results: list[dict]) -> list[dict]:
    keys = ("ref_correct", "ref_security", "vuln_correct", "vuln_security")
    return [
        {
            "id": r["id"],
            "family": r["family"],
            **{
                k: {"passed": r[k].passed, "failed": r[k].failed, "errors": r[k].errors}
                for k in keys
            },
            "problems": r["problems"],
        }
        for r in results
    ]


if __name__ == "__main__":
    results = validate_all()
    bad = [r for r in results if r["problems"]]
    for r in bad:
        print(r["id"], r["problems"])
        for key in ("ref_correct", "ref_security", "vuln_correct", "vuln_security"):
            if not r[key].ok and key.startswith("ref") or key == "vuln_correct" and not r[key].ok:
                print("   ", key, r[key].log[-800:])
    RESULTS_DIR.mkdir(exist_ok=True)
    (RESULTS_DIR / "task_validation.json").write_text(
        json.dumps(to_jsonable(results), indent=2) + "\n", encoding="utf-8"
    )
    print(f"{len(results) - len(bad)}/{len(results)} tasks valid")
    raise SystemExit(1 if bad else 0)
