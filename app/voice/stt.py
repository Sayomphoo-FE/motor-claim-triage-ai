"""Speech-to-Text via faster-whisper.

Uses `large-v3-turbo` (int8 quantised, ~1.5 GB) by default. First call
downloads the model into the HF cache; subsequent calls are instant.

Rationale for faster-whisper over openai-whisper:
- 4-5x faster at equal quality on CPU
- Supports int8 quantisation (smaller RAM footprint)
- Returns word-level timestamps (useful for later diarisation)
"""
from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

DEFAULT_MODEL = os.getenv("WHISPER_MODEL", "large-v3-turbo")
DEFAULT_COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "int8")
DEFAULT_LANGUAGE = os.getenv("WHISPER_DEFAULT_LANG", "")  # empty = auto-detect


@dataclass
class TranscriptionResult:
    text: str
    detected_language: str
    duration_seconds: float
    language_probability: float


@lru_cache(maxsize=1)
def _model():
    # Imported lazily so `import app.voice.stt` is cheap and import-safe
    # even on machines without the model yet.
    from faster_whisper import WhisperModel

    return WhisperModel(
        DEFAULT_MODEL,
        device="cpu",
        compute_type=DEFAULT_COMPUTE_TYPE,
    )


def transcribe(audio: bytes | str | Path, language: str | None = None) -> TranscriptionResult:
    """Transcribe an audio clip.

    Args:
        audio: either raw audio bytes (any format ffmpeg understands) or
            a path to an audio file.
        language: BCP-47 language hint ("th", "en", …). None = auto-detect.
            Hinting is noticeably faster than auto-detect on short clips.
    """
    model = _model()

    if isinstance(audio, bytes):
        # faster-whisper accepts a file path or a numpy array. Writing a
        # temp file is the simplest cross-format path (ffmpeg under the
        # hood will decode mp3/wav/webm/ogg).
        with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as f:
            f.write(audio)
            tmp_path = f.name
        try:
            return _transcribe_path(model, tmp_path, language)
        finally:
            os.unlink(tmp_path)

    return _transcribe_path(model, str(audio), language)


def _transcribe_path(model, path: str, language: str | None) -> TranscriptionResult:
    lang = language or DEFAULT_LANGUAGE or None
    segments, info = model.transcribe(
        path,
        language=lang,
        beam_size=1,
        vad_filter=True,
    )
    text = " ".join(seg.text.strip() for seg in segments).strip()
    return TranscriptionResult(
        text=text,
        detected_language=info.language,
        duration_seconds=info.duration,
        language_probability=info.language_probability,
    )
