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

# from dotenv import load_dotenv
from kokoro import KPipeline
import tempfile

import io
import wave

####
# from transformers import Wav2Vec2Processor, Wav2Vec2ForCTC
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



model = Model.from_pretrained("pyannote/wespeaker-voxceleb-resnet34-LM")
inference = Inference(model, window="whole")
diarization_pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization")

pipeline = KPipeline(lang_code='a')


def preprocess_audio_in_memory(audio_path: str):
    # Step 1: Convert to 16kHz Mono WAV format
    audio = convert_audio_in_memory(input_file=audio_path)
    with open(audio_path, 'rb') as file:
        byte = file.read()

    with open('test.wav', 'wb') as file:
        file.write(byte)

    # audio.export("test.wav", format="wav")

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
                files = {"file": (file.name, file, "audio/m4a")}
                response = await client.post(
                    "https://api.groq.com/openai/v1/audio/transcriptions",
                    headers={
                        "Authorization": f"Bearer {MySettings.GROQ_API_KEY}",
                    },
                    data={
                        "model": "whisper-large-v3-turbo",
                        "response_format": "verbose_json",
                    },
                    files=files,
                )
                return response.json()
    except Exception as e:
        raise e


# model_name = "facebook/wav2vec2-large-960h"
# processor = Wav2Vec2Processor.from_pretrained(model_name)
# wav2vec_model = Wav2Vec2ForCTC.from_pretrained(model_name).to("cuda" if torch.cuda.is_available() else "cpu")

# def wav2vec2_transcribe(audio_path):
#     speech, _ = librosa.load(audio_path, sr=16000)
#     print("cuda" if torch.cuda.is_available() else "cpu")
#     input_values = processor(speech, return_tensors="pt", sampling_rate=16000).input_values
#     logits = wav2vec_model(input_values.to("cuda" if torch.cuda.is_available() else "cpu")).logits
#     predicted_ids = torch.argmax(logits, dim=-1)
#     return processor.batch_decode(predicted_ids)[0].lower()



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
    speaker_segments = [(turn.start, turn.end, speaker) for turn, _, speaker in diarization.itertracks(yield_label=True)]
    return speaker_segments

def extract_embeddings(inference, audio_file, speaker_segments):
    """Extracts embeddings for each speaker segment using the Segment class."""
    speaker_embeddings = {}
    
    for start, end, speaker in speaker_segments:
        segment = Segment(start, end)
        embedding = inference(audio_file, segment)
        if speaker in speaker_embeddings:
            speaker_embeddings[speaker].append(embedding)
        else:
            speaker_embeddings[speaker] = [embedding]
    
    return speaker_embeddings


def merge_or_select_embeddings(speaker_embeddings):
    """Either concatenates or selects the best embedding per speaker."""
    final_embeddings = {}
    for speaker, embeddings in speaker_embeddings.items():
        if len(embeddings) > 1:
            final_embeddings[speaker] = torch.mean(torch.stack(embeddings), dim=0)  # Average embeddings
        else:
            final_embeddings[speaker] = embeddings[0]
    return final_embeddings

def process_audio(audio_file):
    speaker_segments = diarize_audio(diarization_pipeline, audio_file)
    speaker_embeddings = extract_embeddings(inference, audio_file, speaker_segments)
    final_embeddings = merge_or_select_embeddings(speaker_embeddings)
    return final_embeddings