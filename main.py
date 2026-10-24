import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Force UTF-8 encoding on Windows terminals
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Load environment variables
projectRoot = Path(__file__).resolve().parent
load_dotenv(projectRoot / ".env")

from VAD.micProcess import listenForSpeech
from STT.sttClient import transcribeAudio
from NEEDLE.router import routeAndExecute


def handleSpeechUtterance(audioArray, sampleRate):
    """
    Callback triggered by VAD whenever a full spoken sentence is captured.
    Runs asynchronously on worker thread.
    """
    transcriptText = transcribeAudio(audioArray, sampleRate)

    if not transcriptText:
        return

    # Route command through Cactus Needle 3 Edge Router
    routeAndExecute(transcriptText)


def main():
    print("==================================================")
    print(" Voice Action Harness: VAD -> STT -> Router")
    print("==================================================")

    apiKey = os.getenv("ELEVENLABS_API_KEY", "").strip()
    if not apiKey or apiKey == "your_elevenlabs_api_key_here":
        print("[WARNING] ELEVENLABS_API_KEY is not set in .env")
        print("[WARNING] Please add your key to .env to enable transcription.\n")
    else:
        print("[INFO] ElevenLabs STT configured.\n")

    listenForSpeech(onUtterance=handleSpeechUtterance)


if __name__ == "__main__":
    main()
