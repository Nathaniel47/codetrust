import * as vscode from "vscode";
import { insertedLineRange, looksLikeBlockInsertion } from "./insertions";
import { Finding, scanText } from "./rules";

const SEVERITY: Record<Finding["severity"], vscode.DiagnosticSeverity> = {
  error: vscode.DiagnosticSeverity.Error,
  warning: vscode.DiagnosticSeverity.Warning,
  info: vscode.DiagnosticSeverity.Information,
};

// Nothing leaves the machine: the rules run locally and no telemetry is sent.
export function activate(context: vscode.ExtensionContext): void {
  const diagnostics = vscode.languages.createDiagnosticCollection("codetrust");
  context.subscriptions.push(diagnostics);

  const flagged = new Map<string, Map<string, vscode.Diagnostic>>(); // uri -> key -> diagnostic

  function toDiagnostic(finding: Finding, lineOffset: number): vscode.Diagnostic {
    const line = finding.line + lineOffset;
    const diagnostic = new vscode.Diagnostic(
      new vscode.Range(line, finding.start, line, finding.end),
      finding.message,
      SEVERITY[finding.severity]
    );
    diagnostic.source = "CodeTrust";
    diagnostic.code = finding.ruleId;
    return diagnostic;
  }

  function scanRange(doc: vscode.TextDocument, first: number, last: number): void {
    const range = new vscode.Range(first, 0, last, doc.lineAt(last).range.end.character);
    const found = scanText(doc.getText(range));
    const store = flagged.get(doc.uri.toString()) ?? new Map();
    for (const finding of found) {
      const diagnostic = toDiagnostic(finding, first);
      store.set(`${diagnostic.range.start.line}:${finding.ruleId}`, diagnostic);
    }
    flagged.set(doc.uri.toString(), store);
    diagnostics.set(doc.uri, [...store.values()]);
  }

  function scanWholeFile(doc: vscode.TextDocument): void {
    flagged.delete(doc.uri.toString());
    if (doc.lineCount > 0) {
      scanRange(doc, 0, doc.lineCount - 1);
    } else {
      diagnostics.delete(doc.uri);
    }
  }

  context.subscriptions.push(
    vscode.workspace.onDidChangeTextDocument((event) => {
      const doc = event.document;
      if (doc.languageId !== "python") {
        return;
      }
      const mode = vscode.workspace.getConfiguration("codetrust").get<string>("scope", "insertions");
      if (mode === "file") {
        scanWholeFile(doc);
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
          scanRange(doc, first, Math.min(last, doc.lineCount - 1));
        }
      }
    }),
    vscode.workspace.onDidCloseTextDocument((doc) => {
      flagged.delete(doc.uri.toString());
      diagnostics.delete(doc.uri);
    }),
    vscode.commands.registerCommand("codetrust.scanSelection", () => {
      const editor = vscode.window.activeTextEditor;
      if (!editor) {
        return;
      }
      const sel = editor.selection;
      if (sel.isEmpty) {
        scanWholeFile(editor.document);
      } else {
        scanRange(editor.document, sel.start.line, sel.end.line);
      }
      const count = diagnostics.get(editor.document.uri)?.length ?? 0;
      vscode.window.showInformationMessage(
        count === 0 ? "CodeTrust: no risky patterns found." : `CodeTrust: ${count} risky pattern(s) flagged.`
      );
    }),
    vscode.commands.registerCommand("codetrust.clear", () => diagnostics.clear())
  );
}

export function deactivate(): void {}
