"""Turn Semgrep JSON and CodeQL SARIF into one finding list: file, rule, cwe, severity, line."""

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


def codeql_findings(sarif: dict) -> list[dict]:
    findings = []
    for run in sarif.get("runs", []):
        rules = {
            rule["id"]: rule for rule in run.get("tool", {}).get("driver", {}).get("rules", [])
        }
        for r in run.get("results", []):
            rule = rules.get(r.get("ruleId"), {})
            props = rule.get("properties", {})
            tags = props.get("tags", [])
            severity = props.get("security-severity")
            location = (r.get("locations") or [{}])[0].get("physicalLocation", {})
            findings.append(
                {
                    "scanner": "codeql",
                    "file": base_name(location.get("artifactLocation", {}).get("uri", "")),
                    "rule": r.get("ruleId", "").split("/")[-1],
                    "cwe": cwe_numbers(tags),
                    "severity": _codeql_severity(severity, r.get("level")),
                    "line": location.get("region", {}).get("startLine"),
                }
            )
    return findings


def _codeql_severity(security_severity, level) -> str:
    try:
        score = float(security_severity)
    except (TypeError, ValueError):
        return {"error": "high", "warning": "medium"}.get(level or "", "low")
    return "high" if score >= 7 else "medium" if score >= 4 else "low"


def is_high(finding: dict) -> bool:
    return finding["severity"] in ("error", "high", "critical")
