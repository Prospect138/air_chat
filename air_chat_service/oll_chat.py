
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
        logger.debug(f"called funds: {doc.metadata['called_functions']}\n{doc.metadata['full_code']}")
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
            'description': 'Use RAG retriever to get extend context with snippets of code base.',
            'parameters': {
                'type': 'object',
                'properties': {
                    'model_query': {'type': 'string', 'description': 'Query for retriever'},
                },
                'required': ['model_query']
            },
        },
    }

    available_functions = {
        'use_retriever': use_retriever
    }

    model_name = 'devstral:24b'

    messages = []
    system_prompt = Message(role='system', content='Ты — помощник программиста. Твоя задача — найти нужную информацию в кодовой базе,\
                                                    используя RAG. Если первый поиск не дал достаточного результата — задавай уточняющие вопросы,\
                                                    ищи по связанным функциям (например, из поля called_functions), и повторяй поиск.\
                                                    Продолжай, пока не соберёшь полный контекст. Отвечай только после этого. И пиши по-русски. Удачи.')
    messages.append(system_prompt)
    for msg in history:
        messages.append(Message(role=msg['role'], content=msg['content']))
    messages.append(Message(role='user', content=user_message))

    for msg in history:
        messages.append(Message(role=msg['role'], content=msg['content']))
    messages.append(Message(role='user', content=user_message))

    max_tool_calls = 5 
    tool_call_count = 0

    while tool_call_count < max_tool_calls:
        response: ChatResponse = chat(
            model_name,
            messages=messages,
            tools=[use_retriever_tool],
        )

        if not response.message.tool_calls:
            break

        for tool in response.message.tool_calls:
            tool_call_count += 1
            if function_to_call := available_functions.get(tool.function.name):
                output = function_to_call(**tool.function.arguments)
                messages.append(Message(role='tool', content=str(output), name=tool.function.name))
            else:
                continue

        # Запросим модель снова после добавления tool_response
        response = chat(model_name, messages=messages)

        messages.append(response.message)

    final_answer = response.message.content
    new_history = [{'role': m.role, 'content': m.content} for m in messages[1:]]

    return final_answer, new_history

@app.post("/chat", response_model=ChatResponseModel)
def chat_endpoint(req: ChatRequest):
    logger.debug("Получен новый POST-запрос /chat")
    user_message = req.request
    history = req.history if req.history else []
    response, new_history = run_chat(user_message, history)
    return ChatResponseModel(response=response, history=new_history)


db_path = "/home/prospect/oia5g2/air_chat/air_chat_service/code_vector_db"
embeddings = OllamaEmbeddings(model='nomic-embed-text:latest')
vectorstore = FAISS.load_local(db_path, embeddings, allow_dangerous_deserialization=True)
retriever = vectorstore.as_retriever(search_kwargs={'k': 5, 'similarity_score_threshold': 0.8})

if __name__ == "__main__":
    uvicorn.run("oll_chat:app", host="0.0.0.0", port=21666, reload=True)
