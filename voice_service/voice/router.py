import io
import os
import tempfile
import time
from .service import find_user_service, generate_speech_service, add_user_service
from .types import STTRequest, TTSResponse
import av
from typing import Optional
from uuid import UUID

# from pydub import AudioSegment
from dependencies import get_db
from sqlalchemy.orm import Session
from psycopg2.extensions import connection

from fastapi import (
    APIRouter,
    Depends,
    File,
    UploadFile,
    HTTPException,
    BackgroundTasks,
    Depends,
    Body,
    Form,
    Response,
)

voice_router = APIRouter(prefix="/voice", tags=["voice"])


@voice_router.get("/test")
async def test():
    return {"message": "Hello, World!"}


def clean_temp_file(file_path: str):
    """Remove temporary file"""
    try:
        os.unlink(file_path)
    except Exception as e:
        print(f"Error deleting temporary file {file_path}: {e}")


@voice_router.post("/process")
async def process(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user_name: Optional[str] = Body(None),
    conn: connection = Depends(get_db),
):
    print("Processing voice file")
    start = time.time()
    temp_audio_path = await save_upload_file_tmp(file)
    background_tasks.add_task(clean_temp_file, temp_audio_path)

    res = await find_user_service(audio_file_path=temp_audio_path,user_name=user_name, conn= conn)
    return res

@voice_router.post("/add_user")
async def add_user_route(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user_id: str = Form(...),
    conn: connection = Depends(get_db),
):
    print(f"Received file: filename={file.filename}, content_type={file.content_type}")
    temp_audio_path = await save_upload_file_tmp(file)
    background_tasks.add_task(clean_temp_file, temp_audio_path)

    return await add_user_service(audio_file_path=temp_audio_path, user_id=user_id, conn=conn)


@voice_router.post("/tts")
async def generate_speech(
    request:STTRequest,
):
    start = time.time()
    # Get the audio from the text
    audio = generate_speech_service(request.text)
    return Response(
        content=audio,
        media_type="audio/wav",
    )




async def save_upload_file_tmp(upload_file: UploadFile) -> str:
    """Save an upload file temporarily and return its path"""
    try:
        suffix = os.path.splitext(upload_file.filename)[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content = await upload_file.read()
            tmp.write(content)
            return tmp.name
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not save file: {e}")
