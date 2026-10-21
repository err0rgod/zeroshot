"""Native desktop interface for testing Cactus Whistle speech-to-text."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import queue
import threading
import time
import wave
from datetime import datetime

# Keep audio and transcription local by default.
os.environ.setdefault("NEEDLE_TELEMETRY", "0")
os.environ.setdefault("DO_NOT_TRACK", "1")

import needle
import numpy as np
import sounddevice as sd
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

SAMPLE_RATE = 16_000
LANGUAGES = {
    "Auto-detect": None,
    "English": "en",
    "German": "de",
    "French": "fr",
    "Spanish": "es",
    "Italian": "it",
    "Dutch": "nl",
    "Polish": "pl",
}


class WhistleApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Whistle STT — Local Speech to Text")
        self.root.geometry("820x650")
        self.root.minsize(680, 520)

        self.audio_path = tk.StringVar()
        self.language = tk.StringVar(value="Auto-detect")
        self.keywords = tk.StringVar()
        self.word_timestamps = tk.BooleanVar(value=False)
        self.status = tk.StringVar(value="Ready — choose a WAV file or record from your microphone.")

        self._stream: sd.InputStream | None = None
        self._recording_chunks: list[np.ndarray] = []
        self._recording_started = 0.0
        self._recording = False
        self._working = False
        self._live = False
        self._live_audio: queue.Queue[np.ndarray | None] = queue.Queue()
        self._live_resampler: object | None = None
        self._live_committed = ""
        self._events: queue.Queue[tuple[str, object]] = queue.Queue()

        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self._close)
        self.root.bind("<Control-o>", lambda _event: self._browse())
        self.root.bind("<Control-Return>", lambda _event: self._transcribe())
        self.root.after(100, self._poll_events)

    def _build_ui(self) -> None:
        style = ttk.Style()
        style.configure("Title.TLabel", font=("Segoe UI", 18, "bold"))
        style.configure("Subtitle.TLabel", foreground="#555555")
        style.configure("Status.TLabel", foreground="#245b8a")

        outer = ttk.Frame(self.root, padding=18)
        outer.grid(row=0, column=0, sticky="nsew")
        self.root.rowconfigure(0, weight=1)
        self.root.columnconfigure(0, weight=1)
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(3, weight=1)

        ttk.Label(outer, text="Whistle STT", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(
            outer,
            text="Private, on-device transcription using the local Cactus Whistle model",
            style="Subtitle.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(0, 14))

        controls = ttk.LabelFrame(outer, text="Audio and recognition settings", padding=12)
        controls.grid(row=2, column=0, sticky="ew", pady=(0, 12))
        controls.columnconfigure(1, weight=1)

        ttk.Label(controls, text="Audio file:").grid(row=0, column=0, sticky="w", padx=(0, 8))
        ttk.Entry(controls, textvariable=self.audio_path).grid(row=0, column=1, sticky="ew")
        self.browse_button = ttk.Button(controls, text="Browse…", command=self._browse)
        self.browse_button.grid(row=0, column=2, padx=(8, 0))
        self.record_button = ttk.Button(controls, text="● Record microphone", command=self._toggle_recording)
        self.record_button.grid(row=0, column=3, padx=(8, 0))

        ttk.Label(controls, text="Language:").grid(row=1, column=0, sticky="w", padx=(0, 8), pady=(10, 0))
        self.language_box = ttk.Combobox(
            controls,
            textvariable=self.language,
            values=list(LANGUAGES),
            state="readonly",
            width=16,
        )
        self.language_box.grid(row=1, column=1, sticky="w", pady=(10, 0))
        ttk.Checkbutton(
            controls,
            text="Include word timestamps",
            variable=self.word_timestamps,
        ).grid(row=1, column=2, columnspan=2, sticky="w", padx=(8, 0), pady=(10, 0))

        ttk.Label(controls, text="Keywords:").grid(row=2, column=0, sticky="w", padx=(0, 8), pady=(10, 0))
        ttk.Entry(controls, textvariable=self.keywords).grid(
            row=2, column=1, columnspan=3, sticky="ew", pady=(10, 0)
        )
        ttk.Label(
            controls,
            text="Optional comma-separated names or jargon, e.g. Kiro, Cactus Compute",
            style="Subtitle.TLabel",
        ).grid(row=3, column=1, columnspan=3, sticky="w", pady=(2, 0))

        actions = ttk.Frame(controls)
        actions.grid(row=4, column=0, columnspan=4, sticky="ew", pady=(14, 0))
        actions.columnconfigure(0, weight=1)
        actions.columnconfigure(1, weight=1)
        self.transcribe_button = ttk.Button(actions, text="Transcribe file", command=self._transcribe)
        self.transcribe_button.grid(row=0, column=0, sticky="ew")
        self.live_button = ttk.Button(actions, text="● Start live transcription", command=self._toggle_live)
        self.live_button.grid(row=0, column=1, sticky="ew", padx=(8, 0))
        ttk.Button(actions, text="Clear", command=self._clear).grid(row=0, column=2, padx=(8, 0))
        ttk.Button(actions, text="Copy transcript", command=self._copy).grid(row=0, column=3, padx=(8, 0))

        result_frame = ttk.LabelFrame(outer, text="Transcript", padding=10)
        result_frame.grid(row=3, column=0, sticky="nsew")
        result_frame.rowconfigure(0, weight=1)
        result_frame.columnconfigure(0, weight=1)
        self.output = tk.Text(
            result_frame,
            wrap="word",
            font=("Segoe UI", 11),
            padx=8,
            pady=8,
            undo=True,
        )
        scrollbar = ttk.Scrollbar(result_frame, orient="vertical", command=self.output.yview)
        self.output.configure(yscrollcommand=scrollbar.set)
        self.output.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        ttk.Label(outer, textvariable=self.status, style="Status.TLabel").grid(
            row=4, column=0, sticky="ew", pady=(10, 0)
        )

    def _browse(self) -> None:
        if self._recording or self._working:
            return
        selected = filedialog.askopenfilename(
            title="Choose audio to transcribe",
            filetypes=(("WAV audio", "*.wav"), ("All files", "*.*")),
        )
        if selected:
            self.audio_path.set(selected)
            self.status.set("Audio selected. Click Transcribe when ready.")

    def _toggle_recording(self) -> None:
        if self._working:
            return
        if self._recording:
            self._stop_recording()
        else:
            self._start_recording()

    def _start_recording(self) -> None:
        self._recording_chunks = []
        try:
            self._stream = sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=1,
                dtype="float32",
                callback=self._audio_callback,
            )
            self._stream.start()
        except Exception as exc:
            self._stream = None
            messagebox.showerror("Microphone error", str(exc))
            self.status.set("Could not start the microphone.")
            return

        self._recording = True
        self._recording_started = time.monotonic()
        self.record_button.configure(text="■ Stop recording")
        self.browse_button.configure(state="disabled")
        self.transcribe_button.configure(state="disabled")
        self._update_recording_status()

    def _audio_callback(self, data: np.ndarray, _frames: int, _time_info: object, status: object) -> None:
        if status:
            self._events.put(("audio_status", str(status)))
        self._recording_chunks.append(data.copy())

    def _update_recording_status(self) -> None:
        if not self._recording:
            return
        elapsed = time.monotonic() - self._recording_started
        self.status.set(f"Recording… {elapsed:.1f} seconds. Click Stop recording when finished.")
        self.root.after(100, self._update_recording_status)

    def _stop_recording(self) -> None:
        self._recording = False
        stream, self._stream = self._stream, None
        if stream is not None:
            try:
                stream.stop()
                stream.close()
            except Exception as exc:
                messagebox.showwarning("Microphone warning", str(exc))

        self.record_button.configure(text="● Record microphone")
        self.browse_button.configure(state="normal")
        self.transcribe_button.configure(state="normal")
        if not self._recording_chunks:
            self.status.set("No microphone audio was captured.")
            return

        samples = np.concatenate(self._recording_chunks, axis=0).reshape(-1)
        recordings = Path(__file__).resolve().parent / "recordings"
        recordings.mkdir(exist_ok=True)
        path = recordings / f"recording-{datetime.now():%Y%m%d-%H%M%S}.wav"
        pcm = (np.clip(samples, -1.0, 1.0) * 32767).astype("<i2")
        with wave.open(str(path), "wb") as target:
            target.setnchannels(1)
            target.setsampwidth(2)
            target.setframerate(SAMPLE_RATE)
            target.writeframes(pcm.tobytes())
        self.audio_path.set(str(path))
        self.status.set(f"Recording saved ({len(samples) / SAMPLE_RATE:.1f} s). Click Transcribe.")

    def _toggle_live(self) -> None:
        if self._live:
            self._stop_live()
        elif not self._working and not self._recording:
            self._start_live()

    def _start_live(self) -> None:
        import soxr

        keywords = [item.strip() for item in self.keywords.get().split(",") if item.strip()]
        language = LANGUAGES[self.language.get()]
        self._live_audio = queue.Queue()
        self._live_committed = ""
        self.output.delete("1.0", "end")

        try:
            rate = int(sd.query_devices(kind="input")["default_samplerate"])
            self._live_resampler = (
                soxr.ResampleStream(rate, SAMPLE_RATE, 1, dtype="float32", quality="HQ")
                if rate != SAMPLE_RATE
                else None
            )
            self._stream = sd.InputStream(
                samplerate=rate,
                channels=1,
                dtype="float32",
                callback=self._live_audio_callback,
            )
            self._stream.start()
        except Exception as exc:
            self._stream = None
            self._live_resampler = None
            messagebox.showerror("Microphone error", str(exc))
            self.status.set("Could not start live transcription.")
            return

        self._live = True
        self._working = True
        self._set_controls_enabled(False)
        self.live_button.configure(state="normal", text="■ Stop live transcription")
        self.status.set("Live — speak now. Unconfirmed words appear in gray.")
        threading.Thread(
            target=self._streaming_worker,
            args=(language, keywords or None),
            daemon=True,
        ).start()

    def _live_audio_callback(self, data: np.ndarray, _frames: int, _time_info: object, status: object) -> None:
        if status:
            self._events.put(("audio_status", str(status)))
        samples = data[:, 0].copy()
        if self._live_resampler is not None:
            samples = self._live_resampler.resample_chunk(samples)
        if len(samples):
            self._live_audio.put(samples)

    def _live_chunks(self):
        blocks: list[np.ndarray] = []
        held = 0
        while True:
            data = self._live_audio.get()
            if data is not None:
                blocks.append(data)
                held += len(data)
            if blocks and (held >= SAMPLE_RATE or data is None):
                yield np.concatenate(blocks)
                blocks, held = [], 0
            if data is None:
                return

    def _streaming_worker(self, language: str | None, keywords: list[str] | None) -> None:
        try:
            for step in needle.stream(self._live_chunks(), language=language, keywords=keywords):
                self._events.put(("stream_step", step))
            self._events.put(("stream_done", None))
        except Exception as exc:
            self._events.put(("stream_error", str(exc)))

    def _stop_live(self) -> None:
        if not self._live:
            return
        self._live = False
        stream, self._stream = self._stream, None
        if stream is not None:
            try:
                stream.stop()
                stream.close()
            except Exception as exc:
                self._events.put(("audio_status", str(exc)))
        if self._live_resampler is not None:
            tail = self._live_resampler.resample_chunk(np.zeros(0, np.float32), last=True)
            if len(tail):
                self._live_audio.put(tail)
            self._live_resampler = None
        self._live_audio.put(None)
        self.live_button.configure(state="disabled", text="Finishing…")
        self.status.set("Finishing the live transcript…")

    def _show_stream_step(self, payload: object) -> None:
        step = payload if isinstance(payload, dict) else {}
        committed = str(step.get("text") or "").strip()
        if committed:
            self._live_committed += (" " if self._live_committed else "") + committed
        pending = str(step.get("pending") or "").strip()

        self.output.delete("1.0", "end")
        self.output.insert("1.0", self._live_committed)
        if pending:
            if self._live_committed:
                self.output.insert("end", " ")
            self.output.insert("end", pending, "pending")
            self.output.tag_configure("pending", foreground="#777777", font=("Segoe UI", 11, "italic"))
        self.output.see("end")

        received = float(step.get("received") or 0)
        pass_ms = float(step.get("pass_ms") or 0)
        language = step.get("language") or "detecting"
        self.status.set(f"Live — {received:.1f} s received • {pass_ms:.0f} ms/pass • {language}")

    def _finish_live(self) -> None:
        self._live = False
        self._working = False
        self._set_controls_enabled(True)
        self.live_button.configure(text="● Start live transcription")
        if self._live_committed:
            self.status.set("Live transcription complete. Audio stayed on this device.")
        else:
            self.status.set("Live transcription stopped — no speech detected.")

    def _transcribe(self) -> None:
        if self._recording or self._working:
            return
        path = Path(self.audio_path.get().strip()).expanduser()
        if not path.is_file():
            messagebox.showinfo("Choose audio", "Choose a WAV file or record from the microphone first.")
            return
        if path.suffix.lower() != ".wav":
            messagebox.showerror("Unsupported format", "Please choose a WAV file.")
            return

        keywords = [item.strip() for item in self.keywords.get().split(",") if item.strip()]
        language = LANGUAGES[self.language.get()]
        timestamps = self.word_timestamps.get()
        self._working = True
        self._set_controls_enabled(False)
        self.status.set("Transcribing locally…")
        threading.Thread(
            target=self._transcription_worker,
            args=(path, language, keywords or None, timestamps),
            daemon=True,
        ).start()

    def _transcription_worker(
        self,
        path: Path,
        language: str | None,
        keywords: list[str] | None,
        timestamps: bool,
    ) -> None:
        try:
            result = needle.transcribe(
                path,
                language=language,
                keywords=keywords,
                word_timestamps=timestamps,
            )
            self._events.put(("result", result))
        except Exception as exc:
            self._events.put(("error", str(exc)))

    def _poll_events(self) -> None:
        try:
            while True:
                kind, payload = self._events.get_nowait()
                if kind == "result":
                    self._show_result(payload)
                elif kind == "error":
                    self._working = False
                    self._set_controls_enabled(True)
                    self.status.set("Transcription failed.")
                    messagebox.showerror("Transcription error", str(payload))
                elif kind == "stream_step":
                    self._show_stream_step(payload)
                elif kind == "stream_done":
                    self._finish_live()
                elif kind == "stream_error":
                    if self._live:
                        self._stop_live()
                    self._working = False
                    self._set_controls_enabled(True)
                    self.live_button.configure(text="● Start live transcription")
                    self.status.set("Live transcription failed.")
                    messagebox.showerror("Live transcription error", str(payload))
                elif kind == "audio_status":
                    self.status.set(f"Microphone: {payload}")
        except queue.Empty:
            pass
        self.root.after(100, self._poll_events)

    def _show_result(self, payload: object) -> None:
        result = payload if isinstance(payload, dict) else {}
        text = str(result.get("text", ""))
        details = [
            text or "[No speech detected]",
            "",
            f"Language: {result.get('language', 'unknown')}",
            f"Time to first token: {result.get('ttft_ms', 'n/a')} ms",
            f"Decode speed: {result.get('decode_tps', 'n/a')} tokens/s",
        ]
        words = result.get("words")
        if isinstance(words, list) and words:
            details.extend(("", "Word timestamps:"))
            for word in words:
                details.append(
                    f"{word.get('start', 0):>7.2f}–{word.get('end', 0):<7.2f}  "
                    f"{word.get('word', '')}  ({word.get('probability', 0):.3f})"
                )
        self.output.delete("1.0", "end")
        self.output.insert("1.0", "\n".join(details))
        self._working = False
        self._set_controls_enabled(True)
        self.status.set("Transcription complete. Audio stayed on this device.")

    def _set_controls_enabled(self, enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        self.browse_button.configure(state=state)
        self.record_button.configure(state=state)
        self.transcribe_button.configure(state=state)
        self.live_button.configure(state=state)
        self.language_box.configure(state="readonly" if enabled else "disabled")

    def _clear(self) -> None:
        self.output.delete("1.0", "end")
        self.status.set("Ready.")

    def _copy(self) -> None:
        text = self.output.get("1.0", "end-1c")
        if text:
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self.status.set("Transcript copied to the clipboard.")

    def _close(self) -> None:
        if self._recording:
            self._stop_recording()
        if self._live:
            self._stop_live()
        self.root.destroy()


def main() -> None:
    parser = argparse.ArgumentParser(description="Whistle STT desktop interface")
    parser.add_argument("--smoke-test", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()

    root = tk.Tk()
    app = WhistleApp(root)
    if args.smoke_test:
        root.update_idletasks()
        print(json.dumps({"title": root.title(), "status": app.status.get()}))
        root.destroy()
        return
    root.mainloop()


if __name__ == "__main__":
    main()
