"""Run a task's tests against a candidate solution.

This runs the code in a plain subprocess, so it is only for code we wrote (reference and
deliberately vulnerable solutions). Model-generated code goes through the Docker sandbox instead.
"""

import os
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

from codetrust.paths import ROOT
from codetrust.tasks.loader import Task


@dataclass
class TestOutcome:
    passed: int
    failed: int
    errors: int
    timed_out: bool = False
    log: str = ""

    @property
    def ok(self) -> bool:
        return self.passed > 0 and self.failed == 0 and self.errors == 0 and not self.timed_out


def run_tests(task: Task, test_file: str, solution_code: str, timeout: int = 120) -> TestOutcome:
    with tempfile.TemporaryDirectory(prefix="codetrust_") as tmp:
        work = Path(tmp)
        (work / "solution.py").write_text(solution_code, encoding="utf-8")
        shutil.copy(task.path / test_file, work / test_file)
        report = work / "report.xml"
        env = {**os.environ, "PYTHONPATH": str(ROOT), "PYTHONDONTWRITEBYTECODE": "1"}
        cmd = [
            sys.executable,
            "-m",
            "pytest",
            test_file,
            "-q",
            "--tb=short",
            "-p",
            "no:cacheprovider",
            f"--junitxml={report}",
        ]
        try:
            proc = subprocess.run(
                cmd, cwd=work, env=env, capture_output=True, text=True, timeout=timeout
            )
        except subprocess.TimeoutExpired:
            return TestOutcome(0, 0, 0, timed_out=True, log="timeout")
        if not report.exists():
            return TestOutcome(0, 0, 1, log=proc.stdout[-2000:] + proc.stderr[-2000:])
        suite = ET.parse(report).getroot()
        suite = suite if suite.tag == "testsuite" else suite[0]
        total = int(suite.get("tests", 0))
        failed = int(suite.get("failures", 0))
        errors = int(suite.get("errors", 0))
        skipped = int(suite.get("skipped", 0))
        return TestOutcome(
            total - failed - errors - skipped, failed, errors, log=proc.stdout[-3000:]
        )
