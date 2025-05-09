import json, os
from dotenv import find_dotenv, load_dotenv
from fastapi import APIRouter
from dtos.rag import RAGRequest, RAGMultiRequest
from workflows.master.graphs import master_workflow 
from workflows.rag_workflow.graphs import rag_workflow
from workflows.rag_workflow.nodes import query_extractor
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.checkpoint.memory import MemorySaver
from scripts.chat_persistence_service import ChatHistory

# find and load the .env
load_dotenv(find_dotenv())

memory = MemorySaver()

# instantiate a short term memory checkpointer
app = master_workflow.compile()

# instantiate the chat history class
chat_history = ChatHistory(
    mongo_host=os.environ.get('MONGO_HOST'),
    mongo_port=os.environ.get('MONGO_PORT'),
    mongo_user=os.environ.get('MONGO_USER'),
    mongo_pass=os.environ.get('MONGO_PASSWORD'),
    openai_key=os.environ.get('API_KEY'),
    openai_model=os.environ.get('MODEL_NAME'),
    auth_mechanism="SCRAM-SHA-256"
)

rag_router = APIRouter(prefix='/rag', tags=['RAG'])

@rag_router.post("/query")
async def get_response(request: RAGRequest):
    history = chat_history.get_chat_history(request.user_id) 

    if history == None:
        history_as_strings = [
            "None"
        ]
    else:
        history_as_strings = [json.dumps(history[item]) for item in history]

    result = app.invoke(
        {
            "prompt": request.question,
            "user_id": request.user_id,
            "conversation_history": history_as_strings,
        }
    )

    chat_history.save_chat_message(request.user_id, request.question, result)

    return result

@rag_router.post("/multi_query")
def get_multi_response(request: RAGMultiRequest):
    print(request)
    req = request.queries
    prompt = query_extractor(req)

    print(prompt)

    config = {"configurable": {"thread_id": 1}}
        
    # fetch the past messages
    state_snapshot = memory.get(config=config)
    print(state_snapshot)
    history = []
    if state_snapshot:
        conversations = state_snapshot['channel_values']
        if 'conversation_history' in conversations:
            history.extend(conversations['conversation_history'])
        
        # add the prompt
        history.append(
            HumanMessage(content=conversations['prompt'])
        )

        # add the rag response
        history.append(
            AIMessage(content=conversations['generation'])
        )

    result = app.invoke(
    {
        "prompt" : prompt,
        "conversation_history": history
    },
    config=config
    )
    
      
    return result 
