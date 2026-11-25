"""Run Semgrep in Docker over a folder of Python files.

The scanner only reads the files. It runs with no network, as a non-root user, with the code
mounted read-only. The folder holds one file per generation (named after its record).
"""

import json
import subprocess
from pathlib import Path

from codetrust.paths import DATA_DIR
from codetrust.scan.normalise import semgrep_findings

SEMGREP_IMAGE = "semgrep/semgrep:latest"
RULES_DIR = DATA_DIR / "rules"

LOCKDOWN = [
    "--rm", "--network", "none", "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
    "--memory", "5g", "--pids-limit", "512", "--user", "1000:1000",
]  # fmt: skip


def semgrep_command(code_dir: Path, rules_dir: Path = RULES_DIR) -> list[str]:
    return [
        "docker", "run", *LOCKDOWN,
        "-e", "SEMGREP_SEND_METRICS=off",
        "-v", f"{code_dir}:/src:ro",
        "-v", f"{rules_dir}:/rules:ro",
        SEMGREP_IMAGE,
        "semgrep", "--config", "/rules", "--json", "--metrics", "off",
        "--disable-version-check", "--quiet", "--no-git-ignore", "/src",
    ]  # fmt: skip


def run_semgrep(code_dir: Path, rules_dir: Path = RULES_DIR) -> list[dict]:
    proc = subprocess.run(
        semgrep_command(code_dir, rules_dir), capture_output=True, text=True, timeout=1800
    )
    if not proc.stdout.strip():
        raise RuntimeError(f"semgrep produced no output: {proc.stderr[-500:]}")
    data = json.loads(proc.stdout)
    if data.get("errors"):
        # Parse errors in generated code are expected; rule errors are not.
        fatal = [
            e for e in data["errors"] if e.get("type") not in ("PartialParsing", "Syntax error")
        ]
        if fatal:
            raise RuntimeError(f"semgrep errors: {fatal[:2]}")
    return semgrep_findings(data)


VERSION_COMMANDS = {
    "semgrep": [SEMGREP_IMAGE, "semgrep", "--version"],
}


def scanner_versions() -> dict[str, str]:
    """The scanner image is not pinned, so record which version produced a set of results."""
    versions = {}
    for name, arguments in VERSION_COMMANDS.items():
        command = ["docker", "run", "--rm", "--network", "none", *arguments]
        proc = subprocess.run(command, capture_output=True, text=True, timeout=300, check=True)
        versions[name] = proc.stdout.strip().splitlines()[-1]
    return versions


def export_code(records_dir: Path, code_dir: Path) -> int:
    """Write each record's extracted code to <code_dir>/<record file stem>.py."""
    code_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    for path in sorted(records_dir.glob("*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        if record.get("code"):
            (code_dir / f"{path.stem}.py").write_text(record["code"], encoding="utf-8")
            count += 1
    return count


def scan_files(code_dir: Path) -> dict[str, list[dict]]:
    """Return {file stem: [findings]} for every file in code_dir (empty list if clean)."""
    out: dict[str, list[dict]] = {p.stem: [] for p in code_dir.glob("*.py")}
    for finding in run_semgrep(code_dir):
        stem = finding["file"].removesuffix(".py")
        if stem in out:
            out[stem].append(finding)
    return out
