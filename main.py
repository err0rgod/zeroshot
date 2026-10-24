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
from CAMERA.cameraOverlay import startCameraOverlayThread, updateCameraHud


def handleSpeechUtterance(audioArray, sampleRate):
    """
    Callback triggered by VAD whenever a full spoken sentence is captured.
    Runs asynchronously on worker thread.
    """
    transcriptText = transcribeAudio(audioArray, sampleRate)

    if not transcriptText:
        updateCameraHud(status="[LISTENING]", transcript="(no speech detected)")
        return

    updateCameraHud(status="[ROUTING]", transcript=transcriptText)

    # Route command through Cactus Needle 3 Edge Router
    response = routeAndExecute(transcriptText)
    results = response.get("results", [])

    if results:
        actionSummary = str(results[0])
    else:
        actionSummary = response.get("reasoning", "No tool executed")

    updateCameraHud(status="[LISTENING]", action=actionSummary)
    print("[READY] Listening...\n", flush=True)


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

    # Start Always-on-Top Camera Overlay in background thread (starts in FULL mode)
    print("[CAMERA] Launching Camera Overlay (Always on Top)...")
    startCameraOverlayThread()

    listenForSpeech(onUtterance=handleSpeechUtterance)


if __name__ == "__main__":
    main()
