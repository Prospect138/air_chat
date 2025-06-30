
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langchain_ollama import OllamaEmbeddings
from langchain_community.vectorstores import FAISS
from ollama import ChatResponse, chat, Message
import uvicorn

def use_retriever(model_query: str) -> str:
    response_from_retriever = retriever.invoke(model_query)
    result = ''
    for doc in response_from_retriever:
        result += doc.metadata['file_path'] + doc.metadata['full_code']
    return result


# --- FastAPI integration ---
app = FastAPI()

# Allow CORS for local frontend dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    request: str
    history: list = []  # List of {role, content}

class ChatResponseModel(BaseModel):
    response: str
    history: list
    
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("AirChat")

def run_chat(user_message: str, history: list):
    use_retriever_tool = {
        'type': 'function',
        'function': {
            'name': 'use_retriever',
            'description': 'Use RAG retriever to get extend context with snippets of code base',
            'parameters': {
                'type': 'object',
                'required': ['model_query'],
                'properties': {
                    'model_query': {'type': 'string', 'description': 'Query for retriever'}
                },
            },
        },
    }

    available_functions = {
        'use_retriever': use_retriever
    }

    model_name = 'devstral:24b'

    messages = []
    system_prompt = Message(role='system', content='Ты - интеллектуальный помощник программиста, который работает над eNodeB в рамках LTE. Помимо твоей экспертизы в области LTE, EUTRAN и знания 3gpp стандартов, у тебя так же есть доступ к RAG хранилищу с кодовой базой проекта. Перед ответом сверяйся с этой базой данных. И пиши по-русски. Удачи.')
    messages.append(system_prompt)
    for msg in history:
        messages.append(Message(role=msg['role'], content=msg['content']))
    messages.append(Message(role='user', content=user_message))

    response: ChatResponse = chat(
        model_name,
        messages=messages,
        tools=[use_retriever_tool],
        #Сюда добавить аргументы
    )
    
    if response.message.tool_calls:
        for tool in response.message.tool_calls:
            if function_to_call := available_functions.get(tool.function.name):
                output = function_to_call(**tool.function.arguments)
                messages.append(Message(role='tool', content=str(output), name=tool.function.name))
                response = chat(model_name, messages=messages)

            else:
                pass  # function not found
    else:
        messages.append(response.message)
    new_history = []
    for m in messages[1:]:
        new_history.append({'role': m.role, 'content': m.content})
    return response.message.content, new_history

@app.post("/chat", response_model=ChatResponseModel)
def chat_endpoint(req: ChatRequest):
    logger.debug("Получен новый POST-запрос /chat")
    user_message = req.request
    history = req.history if req.history else []
    response, new_history = run_chat(user_message, history)
    return ChatResponseModel(response=response, history=new_history)


db_path = "/home/prospect/oia5g2/code_vector_db"
embeddings = OllamaEmbeddings(model='nomic-embed-text:latest')
vectorstore = FAISS.load_local(db_path, embeddings, allow_dangerous_deserialization=True)
retriever = vectorstore.as_retriever(search_kwargs={'k': 5, 'similarity_score_threshold': 0.8})

if __name__ == "__main__":
    uvicorn.run("oll_chat:app", host="0.0.0.0", port=21666, reload=True)
