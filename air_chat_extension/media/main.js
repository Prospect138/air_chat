// main.js

function addMessage(text, isUser) {
    const chatContainer = document.getElementById('chat-container');
    const messageDiv = document.createElement('div');
    messageDiv.className = isUser ? 'user-message' : 'bot-message';
    messageDiv.textContent = text;
    chatContainer.appendChild(messageDiv);
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

async function sendMessage() {
    const userInput = document.getElementById('user-input');
    const message = userInput.value.trim();
    if (message) {
        addMessage(message, true);
        userInput.value = '';
        try {
            const response = await fetch('http://localhost:21666/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ message: message })
            });
            const data = await response.json();
            if (data.response) {
                addMessage(data.response, false);
            } else if (data.error) {
                addMessage('Ошибка: ' + data.error, false);
            }
        } catch (error) {
            addMessage('Ошибка соединения с сервером', false);
            console.error('Error:', error);
        }
    }
}

// Отправка сообщения по нажатию Enter
document.getElementById('user-input').addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
        sendMessage();
    }
});