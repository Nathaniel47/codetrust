"""Run Semgrep and CodeQL in Docker over a folder of Python files.

Both scanners only read the files. They run with no network, as a non-root user, with the code
mounted read-only. The folder holds one file per generation (named after its record).
"""

import json
import subprocess
from pathlib import Path

from codetrust.paths import DATA_DIR
from codetrust.scan.normalise import codeql_findings, semgrep_findings

SEMGREP_IMAGE = "semgrep/semgrep:latest"
CODEQL_IMAGE = "codetrust-codeql"
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


CODEQL_SUITE = "codeql/python-queries:codeql-suites/python-security-extended.qls"


def codeql_command(code_dir: Path) -> list[str]:
    """One container: build the database and analyse it in an in-memory /work (a Windows bind
    mount made this about 10 times slower), then print the SARIF report on stdout."""
    script = (
        "codeql database create /work/db --language=python --source-root=/src --overwrite >&2 && "
        f"codeql database analyze /work/db {CODEQL_SUITE} --format=sarif-latest "
        "--output=/work/out.sarif --threads=2 --ram=3000 >&2 && cat /work/out.sarif"
    )
    return [
        "docker", "run", *LOCKDOWN,
        "--tmpfs", "/work:rw,exec,uid=1000,gid=1000,size=4g",
        "-v", f"{code_dir}:/src:ro",
        CODEQL_IMAGE, "sh", "-c", script,
    ]  # fmt: skip


def run_codeql(code_dir: Path) -> list[dict]:
    proc = subprocess.run(codeql_command(code_dir), capture_output=True, text=True, timeout=7200)
    if proc.returncode != 0 or not proc.stdout.strip():
        raise RuntimeError(f"codeql failed: {proc.stderr[-800:]}")
    return codeql_findings(json.loads(proc.stdout))


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


def scan_files(code_dir: Path, scanners=("semgrep", "codeql")) -> dict[str, list[dict]]:
    """Return {file stem: [findings]} for every file in code_dir (empty list if clean)."""
    out: dict[str, list[dict]] = {p.stem: [] for p in code_dir.glob("*.py")}
    findings: list[dict] = []
    if "semgrep" in scanners:
        findings += run_semgrep(code_dir)
    if "codeql" in scanners:
        findings += run_codeql(code_dir)
    for finding in findings:
        stem = finding["file"].removesuffix(".py")
        if stem in out:
            out[stem].append(finding)
    return out
