import * as vscode from "vscode";
import { insertedLineRange, looksLikeBlockInsertion } from "./insertions";
import { Finding, scanText } from "./rules";
import { relocate, scanWithSemgrep, withinLines } from "./semgrep";

const SEVERITY: Record<Finding["severity"], vscode.DiagnosticSeverity> = {
  error: vscode.DiagnosticSeverity.Error,
  warning: vscode.DiagnosticSeverity.Warning,
  info: vscode.DiagnosticSeverity.Information,
};

const FILE_MODE_DELAY_MS = 750; // do not start a Semgrep process on every keystroke

// Nothing leaves the machine: scanning is local and no telemetry is sent.
export function activate(context: vscode.ExtensionContext): void {
  const diagnostics = vscode.languages.createDiagnosticCollection("codetrust");
  context.subscriptions.push(diagnostics);
  const rulesFile = context.asAbsolutePath("rules/codetrust.yml");

  const flagged = new Map<string, Map<string, vscode.Diagnostic>>(); // uri -> key -> diagnostic
  // Bumped by "clear", close and whole-file rescans so that late Semgrep results are dropped.
  const generation = new Map<string, number>();
  const timers = new Map<string, NodeJS.Timeout>();
  let warnedAboutSemgrep = false;

  const settings = () => vscode.workspace.getConfiguration("codetrust");
  const current = (key: string) => generation.get(key) ?? 0;

  function forget(key: string): void {
    generation.set(key, current(key) + 1);
    flagged.delete(key);
  }

  function toDiagnostic(finding: Finding): vscode.Diagnostic {
    const diagnostic = new vscode.Diagnostic(
      new vscode.Range(finding.line, finding.start, finding.line, finding.end),
      finding.message,
      SEVERITY[finding.severity]
    );
    diagnostic.source = "CodeTrust";
    diagnostic.code = finding.ruleId;
    return diagnostic;
  }

  function show(doc: vscode.TextDocument, findings: Finding[], replace: boolean): void {
    const key = doc.uri.toString();
    const store = (!replace && flagged.get(key)) || new Map<string, vscode.Diagnostic>();
    for (const finding of findings) {
      store.set(`${finding.line}:${finding.ruleId}`, toDiagnostic(finding));
    }
    flagged.set(key, store);
    diagnostics.set(doc.uri, [...store.values()]);
  }

  // Scan lines first..last (both included); `replace` drops earlier warnings for the file.
  async function scanLines(
    doc: vscode.TextDocument,
    first: number,
    last: number,
    replace: boolean
  ): Promise<void> {
    const config = settings();
    if (!config.get<boolean>("useLocalSemgrep", false)) {
      const range = new vscode.Range(first, 0, last, doc.lineAt(last).range.end.character);
      const found = scanText(doc.getText(range)).map((f) => ({ ...f, line: f.line + first }));
      show(doc, found, replace);
      return;
    }
    // Semgrep needs code that parses, so it gets the whole file and we keep the asked-for lines.
    const key = doc.uri.toString();
    const startedAt = current(key);
    const code = doc.getText();
    const result = await scanWithSemgrep(code, {
      command: config.get<string>("semgrepPath", "semgrep"),
      rulesFile,
    });
    if (result.fallbackReason && !warnedAboutSemgrep) {
      warnedAboutSemgrep = true;
      vscode.window.showWarningMessage(
        `CodeTrust: local Semgrep could not be used (${result.fallbackReason}). ` +
          "Using the built-in rules instead."
      );
    }
    if (doc.isClosed || current(key) !== startedAt) {
      return;
    }
    show(doc, relocate(withinLines(result.findings, first, last), code, doc.getText()), replace);
  }

  async function scanWholeFile(doc: vscode.TextDocument): Promise<void> {
    forget(doc.uri.toString());
    if (doc.lineCount > 0) {
      await scanLines(doc, 0, doc.lineCount - 1, true);
    } else {
      diagnostics.delete(doc.uri);
    }
  }

  function scheduleWholeFile(doc: vscode.TextDocument): void {
    if (!settings().get<boolean>("useLocalSemgrep", false)) {
      void scanWholeFile(doc);
      return;
    }
    const key = doc.uri.toString();
    clearTimeout(timers.get(key));
    timers.set(key, setTimeout(() => void scanWholeFile(doc), FILE_MODE_DELAY_MS));
  }

  context.subscriptions.push(
    vscode.workspace.onDidChangeTextDocument((event) => {
      const doc = event.document;
      if (doc.languageId !== "python") {
        return;
      }
      if (settings().get<string>("scope", "insertions") === "file") {
        scheduleWholeFile(doc);
        return;
      }
      // Drop warnings on lines that were edited, then scan big insertions.
      const store = flagged.get(doc.uri.toString());
      for (const change of event.contentChanges) {
        if (store) {
          for (const [key, d] of store) {
            if (d.range.intersection(change.range)) {
              store.delete(key);
            }
          }
          diagnostics.set(doc.uri, [...store.values()]);
        }
        if (looksLikeBlockInsertion({ text: change.text, rangeLength: change.rangeLength })) {
          const [first, last] = insertedLineRange(change.range.start.line, change.text);
          void scanLines(doc, first, Math.min(last, doc.lineCount - 1), false);
        }
      }
    }),
    vscode.workspace.onDidChangeConfiguration((event) => {
      if (event.affectsConfiguration("codetrust")) {
        warnedAboutSemgrep = false;
      }
    }),
    vscode.workspace.onDidCloseTextDocument((doc) => {
      const key = doc.uri.toString();
      clearTimeout(timers.get(key));
      timers.delete(key);
      forget(key);
      diagnostics.delete(doc.uri);
    }),
    vscode.commands.registerCommand("codetrust.scanSelection", async () => {
      const editor = vscode.window.activeTextEditor;
      if (!editor) {
        return;
      }
      const sel = editor.selection;
      if (sel.isEmpty) {
        await scanWholeFile(editor.document);
      } else {
        await scanLines(editor.document, sel.start.line, sel.end.line, false);
      }
      const count = diagnostics.get(editor.document.uri)?.length ?? 0;
      vscode.window.showInformationMessage(
        count === 0
          ? "CodeTrust: no risky patterns found."
          : `CodeTrust: ${count} risky pattern(s) flagged.`
      );
    }),
    vscode.commands.registerCommand("codetrust.clear", () => {
      for (const key of flagged.keys()) {
        forget(key);
      }
      diagnostics.clear();
    }),
    { dispose: () => timers.forEach((t) => clearTimeout(t)) }
  );
}

export function deactivate(): void {}
