// Optional scanning with the user's own Semgrep, using the rules shipped with the extension.
// No VS Code API here, so it runs in Node tests.
//
// Semgrep is started without a shell, with metrics and the version check off and a local rules
// file, so it has no reason to use the network.
import { execFile } from "node:child_process";
import { mkdtemp, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import * as path from "node:path";
import { Finding, Severity, scanText } from "./rules";

export type Exec = (
  command: string,
  args: string[],
  options: { timeoutMs: number }
) => Promise<string>; // resolves with stdout

export interface SemgrepOptions {
  command: string; // "semgrep" or a full path to it
  rulesFile: string;
  timeoutMs?: number;
  exec?: Exec;
}

export const defaultExec: Exec = (command, args, { timeoutMs }) =>
  new Promise((resolve, reject) => {
    execFile(
      command,
      args,
      {
        timeout: timeoutMs,
        maxBuffer: 10 * 1024 * 1024,
        env: { ...process.env, SEMGREP_SEND_METRICS: "off", PYTHONUTF8: "1" },
        windowsHide: true,
      },
      (error, stdout) => (error ? reject(error) : resolve(stdout))
    );
  });

export function semgrepArgs(rulesFile: string, target: string): string[] {
  return [
    "--config", rulesFile,
    "--json",
    "--metrics", "off",
    "--disable-version-check",
    "--quiet",
    "--no-git-ignore",
    target,
  ];
}

const SEVERITIES: Record<string, Severity> = { ERROR: "error", WARNING: "warning", INFO: "info" };

// Throws when the output cannot be trusted. An empty list must only ever mean "Semgrep read the
// code and found nothing", never "Semgrep could not read it".
export function parseSemgrep(stdout: string, code: string): Finding[] {
  const data = JSON.parse(stdout);
  if (!Array.isArray(data.results)) {
    throw new Error("unexpected Semgrep output");
  }
  if (data.errors?.length) {
    const first = data.errors[0];
    throw new Error(`Semgrep reported an error: ${first.message ?? first.type ?? "unknown"}`);
  }
  const lines = code.split(/\r?\n/);
  return data.results.map((r: any): Finding => {
    const line = r.start.line - 1;
    const length = lines[line]?.length ?? 0;
    const start = Math.min(r.start.col - 1, length);
    const end = r.end.line === r.start.line ? Math.min(r.end.col - 1, length) : length;
    const cweText = String([r.extra?.metadata?.cwe ?? ""].flat()[0]);
    const cwe = Number(/CWE-(\d+)/i.exec(cweText)?.[1] ?? 0);
    return {
      ruleId: String(r.check_id).split(".").pop() as string,
      cwe,
      severity: SEVERITIES[r.extra?.severity] ?? "warning",
      message: `${r.extra?.message ?? "Risky pattern."} (CWE-${cwe})`,
      line,
      start,
      end: Math.max(end, start),
    };
  });
}

export async function runSemgrep(code: string, options: SemgrepOptions): Promise<Finding[]> {
  const exec = options.exec ?? defaultExec;
  // Unsaved text has to be on disk for Semgrep to read it; the copy is removed straight after.
  const dir = await mkdtemp(path.join(tmpdir(), "codetrust-"));
  try {
    const target = path.join(dir, "snippet.py");
    await writeFile(target, code, "utf8");
    const args = semgrepArgs(options.rulesFile, target);
    const stdout = await exec(options.command, args, { timeoutMs: options.timeoutMs ?? 30_000 });
    return parseSemgrep(stdout, code);
  } finally {
    await rm(dir, { recursive: true, force: true });
  }
}

export interface ScanResult {
  findings: Finding[];
  engine: "semgrep" | "builtin";
  fallbackReason?: string;
}

// Scan a whole file with Semgrep; if that fails for any reason, use the built-in rules so a
// missing or broken Semgrep never means "no warnings".
export async function scanWithSemgrep(code: string, options: SemgrepOptions): Promise<ScanResult> {
  try {
    return { findings: await runSemgrep(code, options), engine: "semgrep" };
  } catch (error) {
    const err = error as NodeJS.ErrnoException;
    const reason =
      err.code === "ENOENT" ? `"${options.command}" was not found` : String(err.message ?? err);
    return { findings: scanText(code), engine: "builtin", fallbackReason: reason.slice(0, 300) };
  }
}

export function withinLines(findings: Finding[], first: number, last: number): Finding[] {
  return findings.filter((f) => f.line >= first && f.line <= last);
}

// Semgrep takes seconds, and the file may be edited meanwhile. Move each finding to where its line
// is now (the nearest line with the same text), and drop it if that line no longer exists.
export function relocate(findings: Finding[], before: string, after: string): Finding[] {
  const oldLines = before.split(/\r?\n/);
  const newLines = after.split(/\r?\n/);
  const moved: Finding[] = [];
  for (const finding of findings) {
    const text = oldLines[finding.line];
    let best = -1;
    newLines.forEach((line, i) => {
      if (line === text && (best < 0 || Math.abs(i - finding.line) < Math.abs(best - finding.line))) {
        best = i;
      }
    });
    if (best >= 0) {
      moved.push({ ...finding, line: best });
    }
  }
  return moved;
}
