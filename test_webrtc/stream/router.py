import asyncio
import io
import json
import time
import base64
import wave
import numpy as np
# import cv2
from fastapi import WebSocket, WebSocketDisconnect, APIRouter, Response
from starlette.websockets import WebSocketState
import os
import time
import subprocess

from .service import ProcessRequest
router = APIRouter(prefix="", tags=["voice"])

RHUBARB_PATH = os.path.join("rhubarb", "rhubarb.exe")

# Track processing status
isProcessing = False
isProcessingVideo = False

def convert_to_wav(audio_data: bytes, channels: int = 1, sampwidth: int = 2, framerate: int = 48000) -> bytes:
    """
    Convert raw PCM audio data to a WAV file in memory.
    Assumes 16-bit PCM.
    """
    audio_array = np.frombuffer(audio_data, dtype=np.int16)
    wav_buffer = io.BytesIO()
    with wave.open(wav_buffer, 'wb') as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(sampwidth)
        wav_file.setframerate(framerate)
        wav_file.writeframes(audio_array.tobytes())
    wav_buffer.seek(0)
    return wav_buffer.read()

def exec_command(command):
    """Executes a shell command and returns the output or raises an error."""
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Command failed: {e.stderr}")

def lip_sync_message(message):
    """Converts MP3 to WAV and generates lip-sync JSON."""
    start_time = time.time()
    print(f"Starting conversion for message {message}")
    print(RHUBARB_PATH)

    
    # Convert MP3 to WAV
    # exec_command(f"ffmpeg -y -i audios/message_{message}.mp3 audios/message_{message}.wav")
    # print(f"Conversion done in {int((time.time() - start_time) * 1000)}ms")

    # Generate lip-sync JSON
    exec_command(f'"{RHUBARB_PATH}" -f json -o ./{message}.json ./{message}.wav -r phonetic')
    print(f"Lip sync done in {int((time.time() - start_time) * 1000)}ms")

async def send_results_periodically(websocket: WebSocket, response):
    """
    Send the latest recognition results back to the client every second.
    """
    global isProcessing

    try:
        print("sending response",type(response), response)
        if response and hasattr(response, 'content'):
            byte_string = base64.b64encode(response.content).decode('utf-8')
            # save it temporarly
            # Generate a random UUID
            unique_filename = "generated_audio"

            # Decode the base64 string back to bytes
            audio_bytes = base64.b64decode(byte_string)

            # save the audio temporarly
            with open(unique_filename + '.wav', 'wb') as wav_file:
                wav_file.write(audio_bytes)

             ## generate the lipsync
            lip_sync_message(unique_filename)

            ## load the json
            with open(unique_filename + '.json', 'rb') as json_file:
                lipsync_data = json.load(json_file)

            json_data = {'audio': byte_string,
                         'lipsync': lipsync_data,
                         'valid': True}
            # Send audio content as binary
            asyncio.create_task(websocket.send_text(json.dumps(json_data)))
            time.sleep(1)
            isProcessing = False
    except WebSocketDisconnect:
        print("Client disconnected from periodic sender")


request_handler = ProcessRequest()
isProcessing = False

@router.websocket("/ws/media")
async def websocket_media(websocket: WebSocket):
    """
    WebSocket endpoint that always expects a message with audio.
    Each message should be a JSON object:
      {
         "audio": "<base64-encoded-audio-data>",
         "is_end": true/false
      }
    """
    global isProcessing
    
    await websocket.accept()
    
    try:
        while True:
            # Expect text messages (JSON format) with audio keys.
            message = await websocket.receive_text()
            start = time.time()
            if isProcessing:
                print("Already processing, ignoring new request.")

            else:
                try:
                    isProcessing = True
                    data = json.loads(message)
                except Exception as e:
                    isProcessing = False
                    print("Invalid JSON received:", e)
                    continue

                audio_payload = data.get("audio")

                response = await request_handler(audio_payload)
                if response:
                    end = time.time()
                    print(f'Total TIme: ' , end - start)
                    asyncio.create_task(send_results_periodically(websocket, response))
                else:
                    print("RESPONDED WITH INVALID")
                    json_data = {'valid': False}
                    asyncio.create_task(websocket.send_text(json.dumps(json_data)))
                    isProcessing = False
                     

    except WebSocketDisconnect:
        print("Client disconnected")
    finally:
        if websocket.client_state == WebSocketState.CONNECTED:
            await websocket.close()
        print("WebSocket closed")
    

@router.websocket("/ws/img")
async def websocket_img(websocket: WebSocket):
    """
    WebSocket endpoint that always expects a message with both audio and video.
    Each message should be a JSON object:
      {
         "video": "<base64-encoded-video-data>"
         "is_end": true/false
      }
    """

    global isProcessingVideo
    global isProcessing

    await websocket.accept()

    try:
        while True:
            # Expect text messages (JSON format) with video key.
            message = await websocket.receive_text()
            start = time.time()
            if isProcessingVideo:
                print("Already processing video, ignoring new request.")

            else:
                try:
                    isProcessingVideo = True
                    data = json.loads(message)
                except Exception as e:
                    isProcessingVideo = False
                    print("Invalid JSON received:", e)
                    continue

                video_payload = data.get("video")
                # try:
                response = await request_handler.process_video(video_payload, isProcessing)
                if response:
                    end = time.time()
                    print(f'Video process Total TIme: ', end - start)
                    isProcessingVideo = False
                else:
                    isProcessingVideo = False

    except WebSocketDisconnect:
        print("Client disconnected")
    finally:
        if websocket.client_state == WebSocketState.CONNECTED:
            await websocket.close()
        print("WebSocket closed")
    