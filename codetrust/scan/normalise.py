"""Turn Semgrep JSON into a finding list: file, rule, cwe, severity, line."""

import re

CWE_RE = re.compile(r"cwe[-_ ]?0*(\d+)", re.IGNORECASE)


def cwe_numbers(values) -> list[int]:
    found = []
    for value in values or []:
        for match in CWE_RE.finditer(str(value)):
            number = int(match.group(1))
            if number not in found:
                found.append(number)
    return found


def semgrep_findings(data: dict) -> list[dict]:
    findings = []
    for r in data.get("results", []):
        meta = r.get("extra", {}).get("metadata", {})
        cwe = meta.get("cwe", [])
        cwe = [cwe] if isinstance(cwe, str) else cwe
        findings.append(
            {
                "scanner": "semgrep",
                "file": base_name(r["path"]),
                "rule": r["check_id"].split(".")[-1],
                "cwe": cwe_numbers(cwe),
                "severity": r.get("extra", {}).get("severity", "").lower(),
                "line": r.get("start", {}).get("line"),
            }
        )
    return findings


def base_name(path: str) -> str:
    return path.replace("\\", "/").rsplit("/", 1)[-1]


def is_high(finding: dict) -> bool:
    return finding["severity"] in ("error", "high", "critical")
