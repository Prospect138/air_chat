// main.js

//@ts-check

/**
 * @type {Array<{ role: 'user' | 'assistant' | 'tool', content: string }>}
 */
let chatHistory = [];
let isProcessing = false;

function addMessage(text, role) {
    const chatContainer = document.getElementById('chat-container');
    const messageDiv = document.createElement('div');

    if (role === 'user') {
        messageDiv.className = 'user-message';
    } else if (role === 'assistant') {
        messageDiv.className = 'bot-message';
    } else if (role === 'tool') {
        messageDiv.className = 'tool-message'; // Новый стиль для tool-сообщений
    }

    const iconSpan = document.createElement('span');
    iconSpan.className = 'message-icon';

    if (role === 'user') {
        iconSpan.textContent = '🧑';
    } else if (role === 'assistant') {
        iconSpan.textContent = '🤖';
    } else if (role === 'tool') {
        iconSpan.textContent = '🛠️';
    }

    const textSpan = document.createElement('span');
    textSpan.className = 'message-text';
    textSpan.textContent = text;

    messageDiv.appendChild(iconSpan);
    messageDiv.appendChild(textSpan);
    chatContainer.appendChild(messageDiv);
    chatContainer.scrollTop = chatContainer.scrollHeight;

    chatHistory.push({
        role: role,
        content: text
    });
}

async function sendMessage() {
    if (isProcessing) return;

    const userInput = document.getElementById('user-input');
    const message = userInput.value.trim();
    if (!message) return;

    addMessage(message, 'user');
    userInput.value = '';
    const vscode = acquireVsCodeApi();
    vscode.postMessage({
        command: 'sendMessage',
        value: JSON.stringify({ 
            request: message,
            history: chatHistory
        }) 
    });
    isProcessing = true;
}

window.addEventListener('message', (event) => {
    const response = event.data;
    if (response.command === 'getResponse') {
        const { content, history } = response.payload;
        if (history && history.length > 0)
        {
            redrawChat(history);
        }
        addMessage(content, 'assistant');
        isProcessing = false;
    } else if (response.command === 'errorMessage') {
        addMessage('Ошибка: ' + response.text, false);
    }
});

function redrawChat(history) {
    const chatContainer = document.getElementById('chat-container');
    chatContainer.innerHTML = ''; // очищаем

    for (const msg of history) {
        addMessage(msg.content, msg.role);
    }
}

// Отправка сообщения по нажатию Enter
document.getElementById('user-input').addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
        sendMessage();
    }
});