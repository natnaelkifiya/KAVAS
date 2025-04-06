import time
import uuid
from .repository import identify_user, add_user_to_db
from .utils import (
    pyannote_embed_audio,
    whisper_transcribe,
    # wav2vec2_transcribe ,
    generate_speech,
    preprocess_audio_in_memory,
    process_audio
)

from .types import TranscriptionResponse, CreateUserResponse
import httpx
from psycopg2.extensions import connection


async def find_user_service(*,audio_file_path: str,user_name:str | None, conn: connection,) -> TranscriptionResponse:
    # preprocess
    preprocessed_audio_path = preprocess_audio_in_memory(audio_file_path)


    # pyannote version
    embedded_voice = pyannote_embed_audio(audio_path=preprocessed_audio_path)

    # handle multiple voice
    # embeddings = process_audio(preprocessed_audio_path)

    start = time.time()
    response = await whisper_transcribe(audio_path=audio_file_path)
    transcription = response["text"]
    # transcription = wav2vec2_transcribe(audio_file_path)
    print("time taken for transcription: ", time.time()-start)

    user = identify_user(embedded_voice, conn=conn)
    if not user:
        return TranscriptionResponse(userid=None, transcription=transcription)

    response = TranscriptionResponse(userid=uuid.UUID(user[0]), transcription=transcription, score=user[1])
    return response


def generate_speech_service(text: str) -> bytes:
    text = text.replace('\n', '')

    return generate_speech(text)

async def add_user_service(*,audio_file_path: str,user_id: str, conn: connection) -> CreateUserResponse:
    preprocessed_audio_path = preprocess_audio_in_memory(audio_file_path)

    embedded_voice = pyannote_embed_audio(audio_path=preprocessed_audio_path)
    user_id = add_user_to_db(embedded_voice,user_id=uuid.UUID(user_id), conn=conn) #type: ignore
    return CreateUserResponse(user_id=user_id)