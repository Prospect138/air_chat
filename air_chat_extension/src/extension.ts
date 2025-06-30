import * as vscode from 'vscode';
import * as axios from 'axios'; 

export function activate(context: vscode.ExtensionContext) {
	context.subscriptions.push(
		vscode.commands.registerCommand('AirChat.chat', () => {
			AirChatPanel.createOrShow(context.extensionUri);
		})
	);

	if (vscode.window.registerWebviewPanelSerializer) {
		// Make sure we register a serializer in activation event
		vscode.window.registerWebviewPanelSerializer(AirChatPanel.viewType, {
			async deserializeWebviewPanel(webviewPanel: vscode.WebviewPanel, state: unknown) {
				console.log(`Got state: ${state}`);
				// Reset the webview options so we use latest uri for `localResourceRoots`.
				webviewPanel.webview.options = getWebviewOptions(context.extensionUri);
				AirChatPanel.revive(webviewPanel, context.extensionUri);
				
			}
		});
	}
	//debugger; // Принудительная остановка
    console.log('Extension activated!');
}

function getWebviewOptions(extensionUri: vscode.Uri): vscode.WebviewOptions {
	return {
		// Enable javascript in the webview
		enableScripts: true,

		// And restrict the webview to only loading content from our extension's `media` directory.
		localResourceRoots: [vscode.Uri.joinPath(extensionUri, 'media')]
	};
}

class AirChatPanel {
	/*
	  Track the currently panel. Only allow a single panel to exist at a time.
	 */
	public static currentPanel: AirChatPanel | undefined;

	public static readonly viewType = 'Air Chat';

	private readonly _panel: vscode.WebviewPanel;
	private readonly _extensionUri: vscode.Uri;
	private _disposables: vscode.Disposable[] = [];

	public static createOrShow(extensionUri: vscode.Uri) {
		const column = vscode.window.activeTextEditor
			? vscode.window.activeTextEditor.viewColumn
			: undefined;

		// If we already have a panel, show it.
		if (AirChatPanel.currentPanel) {
			AirChatPanel.currentPanel._panel.reveal(column);
			return;
		}

		// Otherwise, create a new panel.
		const panel = vscode.window.createWebviewPanel(
			AirChatPanel.viewType,
			'CAssist panel',
			column || vscode.ViewColumn.One,
			getWebviewOptions(extensionUri),
		);

		AirChatPanel.currentPanel = new AirChatPanel(panel, extensionUri);
	}

	public static revive(panel: vscode.WebviewPanel, extensionUri: vscode.Uri) {
		AirChatPanel.currentPanel = new AirChatPanel(panel, extensionUri);
	}

	private constructor(panel: vscode.WebviewPanel, extensionUri: vscode.Uri) {
		this._panel = panel;
		this._extensionUri = extensionUri;

		// Set the webview's initial html content
		this._update();

		// Listen for when the panel is disposed
		// This happens when the user closes the panel or when the panel is closed programmatically
		this._panel.onDidDispose(() => this.dispose(), null, this._disposables);

		// Update the content based on view changes
		this._panel.onDidChangeViewState(
			() => {
				if (this._panel.visible) {
					this._update();
				}
			},
			null,
			this._disposables
		);

		this._panel.webview.onDidReceiveMessage(
			async message => {
  				switch (message.command) {
  					case 'sendMessage':
						try {
							const data = JSON.parse(message.value);
							const chat_request = data.request;
							const chat_history = data.history || [];

							const response = await axios.default.post('http://127.0.0.1:21666/chat', {
								request: chat_request,
								history: chat_history
							});

							this._panel.webview.postMessage({
                    	    command: 'getResponse',
                    	    payload: {
								content: response.data.response,
								history: response.data.history
							}
                    	});
						} catch (error) {
							vscode.window.showErrorMessage(`Error on connecting server: ${error}`);
						}
					break;

					case 'alert':
						vscode.window.showErrorMessage(message.text);
						return;
				}
  			},
			null,
			this._disposables
		);
	}

	public dispose() {
		AirChatPanel.currentPanel = undefined;

		// Clean up our resources
		this._panel.dispose();

		while (this._disposables.length) {
			const x = this._disposables.pop();
			if (x) {
				x.dispose();
			}
		}
	}

	private _update() {
		const webview = this._panel.webview;

		// Vary the webview's content based on where it is located in the editor.
		this._panel.webview.html = this._getHtmlForWebview(webview);
	}

	private _getHtmlForWebview(webview: vscode.Webview) {
		// Local path to main script run in the webview
		const scriptPathOnDisk = vscode.Uri.joinPath(this._extensionUri, 'media', 'main.js');

		// And the uri we use to load this script in the webview
		const scriptUri = webview.asWebviewUri(scriptPathOnDisk);

		// Local path to css styles
		const styleResetPath = vscode.Uri.joinPath(this._extensionUri, 'media', 'reset.css');
		const stylesPathMainPath = vscode.Uri.joinPath(this._extensionUri, 'media', 'vscode.css');

		// Uri to load styles into webview
		const stylesResetUri = webview.asWebviewUri(styleResetPath);
		const stylesMainUri = webview.asWebviewUri(stylesPathMainPath);

 		// Use a nonce to only allow specific scripts to be run
		const nonce = getNonce();

		const html_view = 
		`<!DOCTYPE html>
			<html>
			<head>
				<meta charset="UTF-8">

				<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src ${webview.cspSource}; img-src ${webview.cspSource} https:; script-src 'nonce-${nonce}';">

				<meta name="viewport" content="width=device-width, initial-scale=1.0">

				<link href="${stylesResetUri}" rel="stylesheet">
				<link href="${stylesMainUri}" rel="stylesheet">

				<title>Code Assistant</title>
			</head>
			<body>
			    <h1>Air Chat</h1>
			    <div id="chat-container"></div>
			    <input type="text" id="user-input" placeholder="Введите ваше сообщение...">
			    <button onclick="sendMessage()">Отправить</button>
			    <script nonce="${nonce}" src="${scriptUri}"></script>
			</body>
		</html>`;

		return html_view;
	}
}

function getNonce() {
	let text = '';
	const possible = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
	for (let i = 0; i < 32; i++) {
		text += possible.charAt(Math.floor(Math.random() * possible.length));
	}
	return text;
}
