"""Local command-line entry point for Cactus Whistle speech-to-text."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

# The native engine enables telemetry by default. Keep this local wrapper private by default.
os.environ.setdefault("NEEDLE_TELEMETRY", "0")
os.environ.setdefault("DO_NOT_TRACK", "1")

import needle

LANGUAGES = ("en", "de", "fr", "es", "it", "nl", "pl")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Transcribe a WAV file locally with Cactus Whistle."
    )
    parser.add_argument("audio", type=Path, help="Path to a WAV audio file")
    parser.add_argument(
        "--language",
        choices=LANGUAGES,
        help="Force a language (default: auto-detect)",
    )
    parser.add_argument(
        "--keyword",
        action="append",
        dest="keywords",
        metavar="TEXT",
        help="Bias recognition toward a word or phrase; may be repeated",
    )
    parser.add_argument(
        "--word-timestamps",
        action="store_true",
        help="Include per-word start/end times and probabilities",
    )
    parser.add_argument(
        "--text-only",
        action="store_true",
        help="Print only the transcript instead of the full JSON result",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    audio = args.audio.expanduser().resolve()
    if not audio.is_file():
        print(f"Audio file not found: {audio}", file=sys.stderr)
        return 2
    if audio.suffix.lower() != ".wav":
        print("Whistle's Python API accepts WAV files; convert this file to WAV first.", file=sys.stderr)
        return 2

    try:
        result = needle.transcribe(
            audio,
            language=args.language,
            keywords=args.keywords,
            word_timestamps=args.word_timestamps,
        )
    except Exception as exc:
        print(f"Transcription failed: {exc}", file=sys.stderr)
        return 1

    if args.text_only:
        print(result.get("text", ""))
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
