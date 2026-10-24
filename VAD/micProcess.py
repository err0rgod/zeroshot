import sys
from pathlib import Path
import queue
from collections import deque
from concurrent.futures import ThreadPoolExecutor
import numpy as np
import sounddevice as sd

# Force UTF-8 on Windows terminals
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Ensure project root is in sys.path
projectRoot = Path(__file__).resolve().parent.parent
if str(projectRoot) not in sys.path:
    sys.path.append(str(projectRoot))

from STT.sttClient import transcribeAudio

# Audio Configuration (camelCase)
sampleRate = 16000
frameDurationMs = 30
frameSize = int(sampleRate * (frameDurationMs / 1000))  # 480 samples


def calculateRMS(audioChunk: np.ndarray) -> float:
    """Calculate Root Mean Square (RMS) energy of an audio frame."""
    if len(audioChunk) == 0:
        return 0.0
    return float(np.sqrt(np.mean(audioChunk ** 2)))


def listenForSpeech(onUtterance=None):
    """
    Main VAD loop. Listens to microphone, tracks ambient noise,
    slices speech utterances with pre-padding and hangover silence,
    and invokes onUtterance(audioArray, sampleRate) in a background worker.
    """
    audioQueue = queue.Queue()

    # VAD & Noise Floor State
    noiseFloor = 0.02
    minThreshold = 0.04
    thresholdMultiplier = 2.5

    # Slicer State Machine State
    prePadDurationMs = 240
    prePadFrames = int(prePadDurationMs / frameDurationMs)
    prePadBuffer = deque(maxlen=prePadFrames)

    silenceHangoverMs = 750
    silenceHangoverFrames = int(silenceHangoverMs / frameDurationMs)

    minUtteranceFrames = int(400 / frameDurationMs)

    isRecording = False
    silenceCounter = 0
    speechBuffer = []
    utteranceCount = 0

    workerPool = ThreadPoolExecutor(max_workers=2)

    def audioCallback(inData, frameCount, timeInfo, status):
        # Audio callback thread - avoid printing in callback to prevent terminal flooding
        audioQueue.put(inData[:, 0].copy())

    print("[VAD] Initializing microphone...")

    try:
        with sd.InputStream(
            samplerate=sampleRate,
            channels=1,
            dtype="float32",
            blocksize=frameSize,
            callback=audioCallback,
        ):
            print("[VAD] Microphone online. Ready and listening...\n")

            wasRecording = False

            while True:
                audioChunk = audioQueue.get()

                rms = calculateRMS(audioChunk)
                speechThreshold = max(minThreshold, noiseFloor * thresholdMultiplier)
                isSpeech = rms > speechThreshold

                # Dynamic noise floor adaptation during ambient silence
                if not isSpeech and not isRecording:
                    noiseFloor = (0.95 * noiseFloor) + (0.05 * rms)

                # Slicer State Machine
                if isSpeech:
                    if not isRecording:
                        isRecording = True
                        speechBuffer = list(prePadBuffer)
                        silenceCounter = 0
                        print("\n[VOICE DETECTED] Recording...", flush=True)

                    speechBuffer.append(audioChunk)
                    silenceCounter = 0

                else:
                    if isRecording:
                        speechBuffer.append(audioChunk)
                        silenceCounter += 1

                        if silenceCounter >= silenceHangoverFrames:
                            isRecording = False
                            silenceCounter = 0

                            if len(speechBuffer) >= minUtteranceFrames:
                                utteranceCount += 1
                                completeAudio = np.concatenate(speechBuffer)
                                durationSec = len(completeAudio) / sampleRate

                                print(
                                    f"[VOICE COMPLETE] Captured {durationSec:.2f}s audio. Processing...",
                                    flush=True,
                                )

                                if onUtterance:
                                    workerPool.submit(onUtterance, completeAudio, sampleRate)

                            speechBuffer = []
                    else:
                        prePadBuffer.append(audioChunk)

    except KeyboardInterrupt:
        workerPool.shutdown(wait=False)
        print("\n[VAD] Stopped cleanly.")


if __name__ == "__main__":
    listenForSpeech(onUtterance=transcribeAudio)
