"""Transcribe episode MP3s using a local whisper.cpp binary."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from pipeline.config import AUDIO_DIR, TRANSCRIPT_DIR, WHISPER_CPP_BIN, WHISPER_MODEL_PATH
from pipeline.download import audio_path
from pipeline.fetch_feed import fetch_episodes


def transcript_path(number: int) -> Path:
    return TRANSCRIPT_DIR / f"{number}.json"


def _wav_path(mp3: Path) -> Path:
    return mp3.with_suffix(".wav")


def _to_wav_16k(mp3: Path) -> Path:
    wav = _wav_path(mp3)
    if wav.exists() and wav.stat().st_size > 0:
        return wav
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(mp3),
         "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", str(wav)],
        check=True,
    )
    return wav


def _require_whisper() -> None:
    if not WHISPER_MODEL_PATH or not Path(WHISPER_MODEL_PATH).exists():
        sys.exit(
            "WHISPER_MODEL_PATH is unset or points to a missing file. "
            "Download a ggml model (e.g. ggml-medium.en.bin) and set WHISPER_MODEL_PATH in .env."
        )


def transcribe_episode(number: int) -> Path:
    out = transcript_path(number)
    if out.exists() and out.stat().st_size > 0:
        print(f"  skip  {number}  (already transcribed)")
        return out
    _require_whisper()
    TRANSCRIPT_DIR.mkdir(parents=True, exist_ok=True)
    mp3 = audio_path(number)
    if not mp3.exists():
        raise FileNotFoundError(f"Audio not found for episode {number}: {mp3}")
    wav = _to_wav_16k(mp3)
    print(f"  run   whisper on {wav.name}")
    stem = out.with_suffix("")
    subprocess.run(
        [WHISPER_CPP_BIN, "-m", WHISPER_MODEL_PATH, "-f", str(wav),
         "-oj", "-of", str(stem)],
        check=True,
    )
    return out


def main() -> None:
    eps = fetch_episodes()
    for ep in eps:
        transcribe_episode(ep.number)


if __name__ == "__main__":
    main()
