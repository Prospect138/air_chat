# AIR CHAT

AI powered LLM RAG chat for VS code.

## Modules

- air_chat_exstension - source files for vs code exstension
- air_chat_service - python backend, that act as http server and interact with ollama service AND script for build faiss database.

## Diagram
```
1.                                         ---source_codes--->[ProjectParser]--VectorDB--->[RAG]

2. [VS Code extension] -user_query-> [Uvicorn server] -user_query-> [Ollama] -user_query-> [RAG]
                                                                          (optional tool call)

3. [VS Code extension] <-answer------[Uvicorn server] <-answer----- [Ollama] <-answer----- [RAG]
```

## How build:
- install conda enviroment from enviroment.yml
- start ollama service:
```
ollama serve
```
- build database with create_database.py, don't forget to choose dir 
- start oll_chat.py
- open air_chat_exstension/ with vs code, then start it

## TODO
- Refactoring
- clang AST based context enlargement
- containerization
