import os
import torch
import torchaudio
from pyannote.audio import Pipeline, Inference, Model
from pyannote.core import Segment
from pydub import AudioSegment
import httpx

import numpy as np
from scipy.signal import butter, lfilter
from config import MySettings
from pathlib import Path

# from dotenv import load_dotenv
from kokoro import KPipeline, KModel
import tempfile

import io
import wave

####
import torch
import librosa

# load_dotenv()



def normalize(audio, target_amplitude=0.9):
    max_val = np.max(np.abs(audio))
    if max_val > target_amplitude:
        audio *= target_amplitude / max_val
    return audio


def bandpass_filter(data, lowcut, highcut, fs, order=5):
    nyq = 0.5 * fs
    low = lowcut / nyq
    high = highcut / nyq
    b, a = butter(order, [low, high], btype="band")
    y = lfilter(b, a, data)
    return y


cache_dir = Path.home() / ".cache" / "huggingface" / "hub"

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

print("*"*10)
print(f"Using device: {device}")
print("*"*10)

model = Model.from_pretrained("pyannote/wespeaker-voxceleb-resnet34-LM", cache_dir=cache_dir)
model.to(device)
inference = Inference(model, window="whole", device=device)
diarization_pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization", cache_dir=cache_dir)
diarization_pipeline.to(device)


tts_model = KModel(repo_id="hexgrad/Kokoro-82M").to(device).eval()
pipeline = KPipeline(lang_code='a', model=tts_model)


def preprocess_audio_in_memory(audio_path: str):
    # Step 1: Convert to 16kHz Mono WAV format
    audio = convert_audio_in_memory(input_file=audio_path)


    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
        temp_path = temp_file.name
        audio.export(temp_path, format="wav")
        return temp_path


def convert_audio_in_memory(input_file):
    """Convert audio to 16kHz mono WAV format for Pyannote"""
    audio = AudioSegment.from_file(input_file)
    return audio.set_frame_rate(16000).set_channels(1)


def pyannote_embed_audio(audio_path):
    try:
        return inference(audio_path)
    except Exception as e:
        print(f"Error embedding audio file {audio_path}: {e}")
        # Check if file exists and get its size
        if os.path.exists(audio_path):
            size = os.path.getsize(audio_path)
            print(f"File exists, size: {size} bytes")
        else:
            print(f"File does not exist: {audio_path}")
        raise e

async def whisper_transcribe(audio_path: str):
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            with open(audio_path, "rb") as file:
                files = {"file": open(audio_path, "rb")}
                response = await client.post(
                    "https://api.openai.com/v1/audio/transcriptions",
                    headers={
                        "Authorization": f"Bearer {MySettings.OPENAI_API_KEY}",
                    },
                    data = {
                        "model": "whisper-1",
                        "prompt": "Kifiya, chegebeya, Bunna bank, Amhara bank, Enat bank, wegagen bank, zamzam bank, Munir, Natnael"
                    },
                    files=files,
                )
                return response.json()
    except Exception as e:
        raise e



def generate_speech(text:str) -> bytes:
    generator = pipeline(
        text, voice='af_bella', # <= change voice here
        speed=1, split_pattern=r'\n+'
    )

    result = []
    for i, (gs, ps, audio) in enumerate(generator):
        # concatenate the audio segments
        result.append(audio)
    
    if not result:
        raise Exception("No audio generated")
    
    audio_segments = [r.cpu().numpy() for r in result]
    concatenated_audio = np.concatenate(audio_segments)

    sample_rate = 24000

    audio_data = (concatenated_audio * 32767).astype(np.int16)

    wav_io = io.BytesIO()
    with wave.open(wav_io, 'wb') as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 2 bytes per sample (16-bit)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(audio_data.tobytes())
    
    return wav_io.getvalue()

        
def diarize_audio(diarization_pipeline, audio_file):
    """Runs speaker diarization on the given audio file."""
    diarization = diarization_pipeline(audio_file)
    audio = AudioSegment.from_file(audio_file)

    speaker_segments = []
    for turn, _, speaker in diarization.itertracks(yield_label=True):
        start_ms = int(turn.start * 1000)
        end_ms = int(turn.end * 1000)
        segment_audio = audio[start_ms:end_ms]

        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            segment_audio.export(temp_file.name, format="wav")
            speaker_segments.append((speaker, turn.start, turn.end, temp_file.name))
    return speaker_segments

def extract_embeddings(inference, audio_file, speaker_segments):
    """Extracts embeddings for each speaker segment using the Segment class."""
    
    speaker_embeddings  = []
    
    for start, end, speaker, file_path in speaker_segments:
        segment = Segment(start, end)
        embedding = inference(audio_file, segment)
        
        speaker_embeddings.append((start,end,speaker,file_path, embedding))
    return speaker_embeddings


def merge_or_select_embeddings(speaker_embeddings, audio_file):
    """Either concatenates or selects the best embedding per speaker."""
    audio = AudioSegment.from_file(audio_file)



    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
        temp_path = temp_file.name
        audio.export(temp_path, format="wav")
        return temp_path


def process_audio(audio_file):
    speaker_segments = diarize_audio(diarization_pipeline, audio_file)
    speaker_embeddings = extract_embeddings(inference, audio_file, speaker_segments)
    return speaker_embeddings