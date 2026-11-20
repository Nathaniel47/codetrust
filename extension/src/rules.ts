// Pattern rules for risky Python code. Pure functions: no VS Code API here, so they run in Node
// tests and in the evaluation script.
//
// The rules were written by reading the 20 development tasks (their vulnerable and safe
// solutions) and the findings Semgrep and CodeQL gave on them. The 30 test tasks were not used to
// choose or tune them; see results/extension_eval.md for how they score there.

export type Severity = "error" | "warning" | "info";

export interface Rule {
  id: string;
  cwe: number;
  severity: Severity;
  message: string;
  pattern: RegExp; // matched per line, so keep each pattern on one line
}

export interface Finding {
  ruleId: string;
  cwe: number;
  severity: Severity;
  message: string;
  line: number; // 0-based
  start: number;
  end: number;
}

export const RULES: Rule[] = [
  {
    id: "sql-string-built-query",
    cwe: 89,
    severity: "error",
    message: "SQL query built from a formatted string. Use placeholders (?, %s) instead.",
    pattern:
      /\.execute(?:script|many)?\(\s*(?:f["']|["'][^"']*["']\s*(?:%|\+)|["'][^"']*["']\.format\()/,
  },
  {
    id: "html-built-from-fstring",
    cwe: 79,
    severity: "error",
    message: "HTML built by string formatting. Escape inserted values (html.escape or a template).",
    pattern: /\bf["'][^\n]*<[A-Za-z/][^\n]*?\{(?![^}]*escape)[^}]*\}/,
  },
  {
    id: "unescaped-template",
    cwe: 79,
    severity: "error",
    message: "Markup built from a formatted string or marked safe.",
    pattern: /render_template_string\(\s*f["']|Markup\(\s*f["']|\|\s*safe\b/,
  },
  {
    id: "path-joined-with-input",
    cwe: 22,
    severity: "warning",
    message: "File path built from caller input. Resolve it and check it stays inside the folder.",
    pattern: /(?:open|listdir|send_file)\(\s*os\.path\.join\(/,
  },
  {
    id: "shell-command",
    cwe: 78,
    severity: "error",
    message: "Command run through a shell. Pass a list of arguments and leave shell=False.",
    pattern:
      /os\.system\(|os\.popen\(|subprocess\.(?:getoutput|getstatusoutput)\(|shell\s*=\s*True/,
  },
  {
    id: "secret-with-literal-default",
    cwe: 798,
    severity: "error",
    message: "Secret with a hard-coded fallback. Fail or generate a random value when it is unset.",
    pattern:
      /(?:environ\.get|getenv)\(\s*["'][A-Za-z_]*(?:SECRET|PASSWORD|TOKEN|API_?KEY|PRIVATE_?KEY)[A-Za-z_]*["']\s*,\s*["'][^"']+["']/i,
  },
  {
    id: "secret-literal-assigned",
    cwe: 798,
    severity: "error",
    message: "Secret written into the source code. Read it from the environment.",
    pattern:
      /(?:\.secret_key|\bsecret_key|\b\w*(?:password|passwd|api_?key|token)\w*)\s*=\s*["'][^"']{4,}["']/i,
  },
  {
    id: "weak-hash",
    cwe: 327,
    severity: "warning",
    message: "MD5 and SHA-1 are weak. Use PBKDF2/bcrypt for passwords and HMAC-SHA256 for signatures.",
    pattern: /hashlib\.(?:md5|sha1)\(|hashlib\.new\(\s*["'](?:md5|sha1)["']/,
  },
  {
    id: "ecb-mode",
    cwe: 327,
    severity: "error",
    message: "ECB mode leaks patterns. Use an authenticated mode such as AES-GCM.",
    pattern: /modes\.ECB\(|MODE_ECB/,
  },
  {
    id: "predictable-random",
    cwe: 338,
    severity: "warning",
    message: "random is predictable. Use the secrets module for tokens, codes and keys.",
    pattern: /\brandom\.(?:choice|choices|randint|randrange|getrandbits|random)\(/,
  },
  {
    id: "unsafe-deserialization",
    cwe: 502,
    severity: "error",
    message: "Loading untrusted data this way can run code. Use JSON or yaml.safe_load.",
    pattern:
      /pickle\.loads?\(|marshal\.loads?\(|yaml\.unsafe_load\(|yaml\.load\((?![^)]*Safe)[^)]*\)/,
  },
  {
    id: "request-to-variable-url",
    cwe: 918,
    severity: "info",
    message: "Server-side request to a variable URL. Block private and internal addresses.",
    pattern: /requests\.(?:get|post|head|put|delete)\(\s*[A-Za-z_]|urlopen\(\s*[A-Za-z_]/,
  },
  {
    id: "redirect-to-request-value",
    cwe: 601,
    severity: "error",
    message: "Redirect target comes straight from the request. Allow only local paths.",
    pattern: /redirect\(\s*request\.(?:args|form|values)/,
  },
  {
    id: "upload-saved-under-client-name",
    cwe: 434,
    severity: "error",
    message: "Upload saved under the client's file name. Check the type and use secure_filename.",
    pattern: /\.save\(\s*os\.path\.join\((?![^)]*secure_filename)[^)]*\.filename/,
  },
];

interface LogicalLine {
  text: string; // physical lines of one statement joined with spaces
  line: number; // 0-based first physical line
  firstLength: number; // length of the first physical line
}

const MAX_JOINED_LINES = 12; // stop joining if brackets never close (probably a syntax error)

// Calls are often split over several lines, so rules see a whole statement at a time: lines are
// joined until the brackets opened on them are closed again.
export function logicalLines(text: string): LogicalLine[] {
  const physical = text.split(/\r?\n/);
  const out: LogicalLine[] = [];
  for (let i = 0; i < physical.length; i++) {
    let joined = physical[i];
    let depth = bracketDepth(joined);
    let j = i;
    while (depth > 0 && j + 1 < physical.length && j - i < MAX_JOINED_LINES) {
      j++;
      joined += " " + physical[j].trim();
      depth += bracketDepth(physical[j]);
    }
    out.push({ text: joined, line: i, firstLength: physical[i].length });
  }
  return out;
}

function bracketDepth(line: string): number {
  let depth = 0;
  for (const ch of line.replace(/#.*$/, "")) {
    if ("([{".includes(ch)) {
      depth++;
    } else if (")]}".includes(ch)) {
      depth--;
    }
  }
  return depth;
}

export function scanText(text: string, rules: Rule[] = RULES): Finding[] {
  const findings: Finding[] = [];
  const seen = new Set<string>();
  for (const logical of logicalLines(text)) {
    if (/^\s*#/.test(logical.text)) {
      continue; // commented-out code is not a risk
    }
    for (const rule of rules) {
      const match = rule.pattern.exec(logical.text);
      if (!match) {
        continue;
      }
      const key = `${logical.line}:${rule.id}`;
      if (seen.has(key)) {
        continue;
      }
      seen.add(key);
      const inFirstLine = match.index < logical.firstLength;
      findings.push({
        ruleId: rule.id,
        cwe: rule.cwe,
        severity: rule.severity,
        message: `${rule.message} (CWE-${rule.cwe})`,
        line: logical.line,
        start: inFirstLine ? match.index : 0,
        end: inFirstLine ? Math.min(match.index + match[0].length, logical.firstLength) : logical.firstLength,
      });
    }
  }
  return findings;
}
