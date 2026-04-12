import * as vscode from 'vscode';
import * as https from 'https';

export function activate(context: vscode.ExtensionContext) {
    const statusBar = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
    statusBar.text = '$(shield) Sgraal';
    statusBar.show();
    context.subscriptions.push(statusBar);

    context.subscriptions.push(
        vscode.commands.registerCommand('sgraal.preflight', async () => {
            const editor = vscode.window.activeTextEditor;
            if (!editor) return;
            const selection = editor.document.getText(editor.selection);
            if (!selection) { vscode.window.showWarningMessage('Select memory_state JSON first'); return; }
            try {
                const config = vscode.workspace.getConfiguration('sgraal');
                const result = await runPreflight(JSON.parse(selection), config);
                const decision = result.recommended_action;
                statusBar.text = decision === 'USE_MEMORY' ? '$(check) USE_MEMORY' :
                    decision === 'WARN' ? '$(warning) WARN' : '$(error) BLOCK';
                vscode.window.showInformationMessage(`Sgraal: ${decision} (omega: ${result.omega_mem_final})`);
            } catch (e: any) { vscode.window.showErrorMessage(`Sgraal error: ${e.message}`); }
        })
    );
}

async function runPreflight(memoryState: any[], config: vscode.WorkspaceConfiguration): Promise<any> {
    const apiKey = config.get<string>('apiKey', 'sg_demo_playground');
    const apiUrl = config.get<string>('apiUrl', 'https://api.sgraal.com');
    const domain = config.get<string>('defaultDomain', 'general');
    const body = JSON.stringify({ memory_state: memoryState, domain, action_type: 'reversible' });
    const resp = await fetch(`${apiUrl}/v1/preflight`, {
        method: 'POST', headers: { 'Authorization': `Bearer ${apiKey}`, 'Content-Type': 'application/json' }, body,
    });
    return resp.json();
}

export function deactivate() {}
