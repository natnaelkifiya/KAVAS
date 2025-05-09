import os
from dotenv import find_dotenv, load_dotenv
from fastapi import APIRouter, HTTPException
from typing import Dict
from scripts.chat_persistence_service import ChatHistory  # Import your existing function

# find and load the .env
load_dotenv(find_dotenv())


user_router = APIRouter(prefix="/users", tags=["users"])

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


@user_router.get("/{user_id}/details", response_model=Dict[str, str])
async def fetch_user_details(user_id: str):
    """
    Get stored details for a user (name, job, etc.).
    """
    details = chat_history.get_user_details(user_id)
    if not details:
        raise HTTPException(status_code=404, detail="User not found")
    return details

@user_router.get("/{user_id}/greet", response_model=Dict[str, str])
async def greet_user(user_id: str):
    """
    Greet the user with their stored name and job.
    """
    greeting = chat_history.greet_user(user_id=user_id)
    return {"generation": greeting}