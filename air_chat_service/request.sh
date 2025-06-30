curl -X POST "http://localhost:21666/chat" \
     -H "Content-Type: application/json" \
     -d '{
           "request": "Привет! Как дела?",
           "history": []
         }'
