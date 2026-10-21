# Local Cactus Whistle STT

A local desktop and command-line interface for [Cactus-Compute/whistle](https://huggingface.co/Cactus-Compute/whistle), powered by the official `cactus-needle` Python package. Whistle supports English, German, French, Spanish, Italian, Dutch, and Polish.

> **GPU note:** Whistle's official runtime is CPU-only. It works on a GPU-equipped laptop, but it does not use CUDA or the GPU. See [setup.md](setup.md) for installation details and troubleshooting.

## Desktop interface

After completing [setup.md](setup.md), double-click **`Launch Whistle STT.bat`** on Windows, or launch it from PowerShell:

```powershell
.\"Launch Whistle STT.bat"
```

In the window, you can:

1. Click **Start live transcription**, speak, and watch committed text appear while unconfirmed words are shown in gray. Click **Stop live transcription** to flush the final words.
2. Click **Browse** and choose a WAV file, then click **Transcribe file**.
3. Click **Record microphone**, speak, click **Stop recording**, then click **Transcribe file** to review a saved recording before transcription.

You can select a language, enter comma-separated keyword hints, request word timestamps for file transcription, and copy the result. Recordings are saved under `recordings/` and remain on the laptop.

## Command-line transcription

From PowerShell in the repository folder:

```powershell
.\.venv\Scripts\python.exe .\transcribe.py .\your-audio.wav
```

Useful options:

```powershell
# Only the transcript
.\.venv\Scripts\python.exe .\transcribe.py .\your-audio.wav --text-only

# Force English and include word timings
.\.venv\Scripts\python.exe .\transcribe.py .\your-audio.wav --language en --word-timestamps

# Bias recognition toward names or jargon (repeat as needed)
.\.venv\Scripts\python.exe .\transcribe.py .\your-audio.wav --keyword "Kiro" --keyword "Cactus Compute"
```

The full JSON result contains `text`, detected `language`, time to first token (`ttft_ms`), and decoding speed (`decode_tps`). With `--word-timestamps`, it also contains a `words` array.

## Official microphone playground

```powershell
$env:NEEDLE_TELEMETRY="0"
$env:DO_NOT_TRACK="1"
.\.venv\Scripts\needle.exe whistle playground
```

Press `Ctrl+C` to stop. Microphone access may require enabling Windows **Settings > Privacy & security > Microphone > Let desktop apps access your microphone**.

## Audio and offline behavior

- WAV is accepted directly. Whistle works internally at 16 kHz mono; `soxr` resamples other WAV rates, and multichannel WAV is mixed to mono.
- MP3, M4A, and other compressed formats must first be converted to WAV.
- The native engine and model weights are fetched on the first transcription and cached locally. Later transcriptions can work offline.
- The project GUI and CLI disable Needle telemetry by default.

## Repository files

- `whistle_gui.py` — desktop UI with live and file transcription
- `transcribe.py` — command-line WAV transcription
- `Launch Whistle STT.bat` — Windows desktop launcher
- `requirements.lock.txt` — exact tested dependency versions
- `setup.md` — complete installation and troubleshooting guide
