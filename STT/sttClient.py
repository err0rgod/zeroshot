import io
import os
import sys
import time
import wave
import numpy as np
import requests
from dotenv import load_dotenv
from pathlib import Path

# Force UTF-8 on Windows terminals to prevent charmap encoding errors
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Load environment variables from project root .env
projectRoot = Path(__file__).resolve().parent.parent
load_dotenv(projectRoot / ".env")


def audioToWavBytes(audioArray: np.ndarray, sampleRate: int = 16000) -> bytes:
    """Convert a float32 NumPy audio array to 16-bit PCM WAV bytes in memory."""
    # Clip and scale float32 [-1.0, 1.0] to int16 [-32768, 32767]
    pcmData = (np.clip(audioArray, -1.0, 1.0) * 32767).astype(np.int16)

    wavBuffer = io.BytesIO()
    with wave.open(wavBuffer, "wb") as wavFile:
        wavFile.setnchannels(1)  # Mono
        wavFile.setsampwidth(2)  # 16-bit
        wavFile.setframerate(sampleRate)
        wavFile.writeframes(pcmData.tobytes())

    return wavBuffer.getvalue()


def transcribeAudio(audioArray: np.ndarray, sampleRate: int = 16000) -> str:
    """Send an audio array to ElevenLabs Speech-to-Text API and return transcription."""
    apiKey = os.getenv("ELEVENLABS_API_KEY", "").strip()

    if not apiKey or apiKey == "your_elevenlabs_api_key_here":
        print("\n[STT ERROR] ELEVENLABS_API_KEY not found in .env! Please paste your key.")
        return ""

    wavBytes = audioToWavBytes(audioArray, sampleRate)
    apiUrl = "https://api.elevenlabs.io/v1/speech-to-text"
    headers = {"xi-api-key": apiKey}

    files = {
        "file": ("audio.wav", wavBytes, "audio/wav")
    }
    data = {
        "model_id": "scribe_v1"
    }

    startTime = time.perf_counter()
    try:
        response = requests.post(apiUrl, headers=headers, files=files, data=data, timeout=10)
        latencyMs = int((time.perf_counter() - startTime) * 1000)

        if response.status_code == 200:
            result = response.json()
            transcriptText = result.get("text", "").strip()
            if transcriptText:
                print(f"\n\n[TRANSCRIPT ({latencyMs}ms)]: \"{transcriptText}\"\n")
            else:
                print(f"\n\n[INFO ({latencyMs}ms)]: (No speech detected in audio slice)\n")
            return transcriptText
        else:
            print(f"\n\n[ERROR] [STT API Error {response.status_code} ({latencyMs}ms)]: {response.text}\n")
            return ""

    except Exception as error:
        print(f"\n[ERROR] [STT Request Failed]: {error}\n")
        return ""
