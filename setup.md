# Setup

This guide installs the local Whistle speech-to-text app on another laptop. The tested configuration is Windows 11 x64 with Python 3.13; the `cactus-needle` package declares support for Python 3.9 or newer.

## GPU note

Whistle's official Cactus Needle runtime is CPU-only. A laptop with an NVIDIA, AMD, or Intel GPU can run this project, but Whistle will not use the GPU or its VRAM. You do **not** need CUDA, cuDNN, PyTorch, or a GPU driver beyond what the laptop normally uses.

This is expected behavior, not a configuration problem. Whistle is a small quantized model designed for efficient on-device CPU inference. If GPU acceleration is mandatory, use a GPU-oriented STT backend such as Whisper/faster-whisper instead of Whistle.

## Requirements

- Windows 10/11 x64 or ARM64, or a supported 64-bit Linux system
- Python 3.9 or newer; Python 3.13 is recommended because it is tested here
- Git, if cloning the repository
- Internet access for package installation and the first model download
- A microphone for recording or live transcription
- Approximately 500 MB of free disk space for the environment and download caches

The model itself is about 17 MB. The native engine is downloaded automatically for the current operating system and CPU architecture.

## 1. Clone the repository

```powershell
git clone https://github.com/err0rgod/zeroshot.git
cd zeroshot
```

If you copied the folder directly, open PowerShell in that folder instead.

## 2. Create the environment

### Recommended: uv

Install [uv](https://docs.astral.sh/uv/) if it is not already available, then run:

```powershell
uv venv .venv --python 3.13
uv pip sync --python .\.venv\Scripts\python.exe .\requirements.lock.txt
```

### Alternative: standard Python and pip

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r .\requirements.lock.txt
```

All runtime dependency versions are pinned in `requirements.lock.txt`.

## 3. Verify the installation

```powershell
.\.venv\Scripts\python.exe -c "import needle, numpy, sounddevice, soxr; print('Whistle dependencies OK')"
.\.venv\Scripts\python.exe .\whistle_gui.py --smoke-test
```

The second command should print JSON containing the window title and ready status.

To list detected audio devices:

```powershell
.\.venv\Scripts\python.exe -c "import sounddevice as sd; print(sd.query_devices())"
```

## 4. Start the desktop app

On Windows, double-click `Launch Whistle STT.bat`, or run:

```powershell
.\"Launch Whistle STT.bat"
```

Use **Start live transcription** for real-time microphone text. Stable words appear normally and the current unconfirmed tail appears in gray. You can also record audio first or browse to an existing WAV file.

The first transcription downloads the native engine and `whistle.cact` weights from Hugging Face. Subsequent runs use the local cache.

## 5. Test from the command line

```powershell
.\.venv\Scripts\python.exe .\transcribe.py .\sample.wav
```

Options:

```powershell
# Plain transcript
.\.venv\Scripts\python.exe .\transcribe.py .\sample.wav --text-only

# Force English and include per-word timing
.\.venv\Scripts\python.exe .\transcribe.py .\sample.wav --language en --word-timestamps

# Favor expected names or terminology
.\.venv\Scripts\python.exe .\transcribe.py .\sample.wav --keyword "Kiro" --keyword "Cactus Compute"
```

Supported languages are English (`en`), German (`de`), French (`fr`), Spanish (`es`), Italian (`it`), Dutch (`nl`), and Polish (`pl`).

## Linux notes

Create the environment with Linux paths:

```bash
python3.13 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.lock.txt
.venv/bin/python whistle_gui.py
```

The desktop GUI requires Tk and microphone capture requires PortAudio. On Debian/Ubuntu, install missing system libraries with:

```bash
sudo apt-get update
sudo apt-get install python3-tk libportaudio2
```

The Windows `.bat` launcher is not used on Linux.

## Audio formats

- WAV files are supported directly.
- Audio is converted internally to 16 kHz mono; the pinned `soxr` dependency handles WAV resampling.
- MP3, M4A, and other compressed formats must be converted to WAV first. FFmpeg is optional and is not installed by this project.
- Microphone recordings made by the GUI are stored in `recordings/`, which Git ignores.

## Privacy and offline use

The GUI and `transcribe.py` set `NEEDLE_TELEMETRY=0` and `DO_NOT_TRACK=1` before loading Needle. Audio and transcripts stay on the laptop. Model and engine files are fetched from Hugging Face once and cached under:

- Windows: `%USERPROFILE%\.cache\cactus-needle`
- Linux: `~/.cache/cactus-needle`

After one successful transcription, the app can run offline. To disable telemetry when using the official Needle CLI directly:

```powershell
$env:NEEDLE_TELEMETRY="0"
$env:DO_NOT_TRACK="1"
.\.venv\Scripts\needle.exe whistle playground
```

## Troubleshooting

### The GPU shows 0% usage

That is correct. The official Whistle engine executes on the CPU and has no CUDA/ROCm/DirectML mode.

### No microphone or permission denied

On Windows, enable **Settings > Privacy & security > Microphone > Let desktop apps access your microphone**. Check device detection with the command in step 3.

### A Hugging Face symlink warning appears on Windows

The warning is harmless; downloads still work but may use additional cache space. Enabling Windows Developer Mode permits efficient cache symlinks, but it is optional.

### A non-WAV file is rejected

Convert it to WAV first. A typical FFmpeg command, if FFmpeg is installed, is:

```powershell
ffmpeg -i input.mp3 -ar 16000 -ac 1 output.wav
```

### Rebuild the environment

Delete `.venv`, then repeat step 2. Do not commit `.venv`, model caches, recordings, or audio files to Git.
