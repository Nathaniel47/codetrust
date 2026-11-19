import * as vscode from "vscode";

export function activate(context: vscode.ExtensionContext): void {
  // Placeholder: rules and inline diagnostics arrive in Step 5.
  context.subscriptions.push(
    vscode.commands.registerCommand("codetrust.scanSelection", () => {
      vscode.window.showInformationMessage("CodeTrust: scanner not implemented yet.");
    })
  );
}

export function deactivate(): void {}
