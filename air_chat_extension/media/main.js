// main.js

//@ts-check

/**
 * @type {Array<{ role: 'user' | 'assistant', content: string }>}
 */

let chatHistory = [];

function addMessage(text, isUser) {
    const chatContainer = document.getElementById('chat-container');
    const messageDiv = document.createElement('div');
    messageDiv.className = isUser ? 'user-message' : 'bot-message';
    messageDiv.textContent = text;
    chatContainer.appendChild(messageDiv);
    chatContainer.scrollTop = chatContainer.scrollHeight;

    chatHistory.push({
        role: isUser ? 'user' : 'assistant',
        content: text
    });
}

async function sendMessage() {
    const userInput = document.getElementById('user-input');
    const message = userInput.value.trim();
    if (!message) return;

    addMessage(message, true);
    userInput.value = '';
    const vscode = acquireVsCodeApi();
    vscode.postMessage({
        command: 'sendMessage',
        value: JSON.stringify({ 
            request: message,
            history: chatHistory
        }) 
    });
}

window.addEventListener('message', (event) => {
    const response = event.data;
    if (response.command === 'getResponse') {
        const { content, history } = response.payload;
        if (history && history.legth > 0)
        {
            redrawChat(history);
        }
        addMessage(content, false);
    } else if (response.command === 'errorMessage') {
        addMessage('Ошибка: ' + response.text, false);
    }
});

function redrawChat(history) {
    const chatContainer = document.getElementById('chat-container');
    chatContainer.innerHTML = ''; // очищаем

    for (const msg of history) {
        addMessage(msg.content, msg.role === 'user');
    }
}

// Отправка сообщения по нажатию Enter
document.getElementById('user-input').addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
        sendMessage();
    }
});