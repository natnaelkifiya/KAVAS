from pydantic import BaseModel
from uuid import UUID


class TranscriptionResponse(BaseModel):
    userid: UUID |None
    score: float = 0.0
    transcription: str |None


class CreateUserResponse(BaseModel):
    user_id: UUID

class STTRequest(BaseModel):
    text:str

class TTSResponse(BaseModel):
    audio: bytes
    media_type: str