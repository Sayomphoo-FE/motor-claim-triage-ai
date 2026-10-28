"""Text-to-Speech via Microsoft Edge-TTS.

Uses free Microsoft Neural voices via the Edge browser's internal
endpoint. No API key required. Returns MP3 bytes for direct
`st.audio()` playback.

Voices:
  th: PremwadeeNeural (female) is the warmest Thai Neural voice.
  en: AriaNeural (female) is Microsoft's default US English voice.

Both are Neural TTS, not Standard — quality is comparable to Azure
Speech paid tier.
"""
from __future__ import annotations

import asyncio
import os
import re

from dotenv import load_dotenv

load_dotenv()

VOICE_BY_LANG: dict[str, str] = {
    "th": os.getenv("TTS_VOICE_TH", "th-TH-PremwadeeNeural"),
    "en": os.getenv("TTS_VOICE_EN", "en-US-AriaNeural"),
}

# Slower default — natural pace for a call-centre persona + helps Thai
# listeners track technical details.
DEFAULT_RATE = os.getenv("TTS_RATE", "-20%")


_THAI_CHARS_RE = re.compile(r"[฀-๿]")


def detect_lang(text: str) -> str:
    """Trivial Thai vs English detector based on Unicode range."""
    return "th" if _THAI_CHARS_RE.search(text) else "en"


def _normalise(text: str) -> str:
    """Fix content patterns that make Edge-TTS return 'no audio'.

    - Insert a space between a Thai char and an adjacent Latin char
      (e.g. "ของABC" → "ของ ABC"). The Microsoft service silently
      drops some mixed-script tokens with no delimiter.
    - Collapse multiple spaces.
    """
    import re

    text = re.sub(r"([฀-๿])([A-Za-z0-9])", r"\1 \2", text)
    text = re.sub(r"([A-Za-z0-9])([฀-๿])", r"\1 \2", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _split_sentences(text: str) -> list[str]:
    """Split on Thai + English sentence terminators, preserving them."""
    import re

    parts = re.split(r"(?<=[\.\?!。ค่ะคะครับนะคะนะครับ])\s+", text)
    return [p.strip() for p in parts if p.strip()]


async def _synthesize_chunk(text: str, voice: str, rate: str) -> bytes:
    """Return MP3 bytes for one chunk, or b'' if Edge-TTS yields nothing."""
    import edge_tts
    from edge_tts.exceptions import NoAudioReceived

    buf = bytearray()
    try:
        communicate = edge_tts.Communicate(text, voice=voice, rate=rate)
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                buf.extend(chunk["data"])
    except NoAudioReceived:
        return b""
    return bytes(buf)


async def _synthesize_async(text: str, voice: str, rate: str) -> bytes:
    """Synthesize sentence-by-sentence.

    Splitting always (not just on failure) gives:
    - Natural pauses between sentences (the gap between MP3 streams
      becomes a brief silence when played back).
    - Robustness against Edge-TTS's "NoAudioReceived" bug on
      long mixed-script content — if one sentence fails we drop it
      instead of losing the whole message.
    """
    normalised = _normalise(text)
    sentences = _split_sentences(normalised) or [normalised]

    out = bytearray()
    for sentence in sentences:
        chunk = await _synthesize_chunk(sentence, voice, rate)
        if chunk:
            out.extend(chunk)
    return bytes(out)


def synthesize(text: str, lang: str | None = None, rate: str = DEFAULT_RATE) -> bytes:
    """Synthesize text to MP3 audio bytes.

    Args:
        text: free-text content.
        lang: "th", "en", or None to auto-detect from text.
        rate: Edge-TTS rate string, e.g. "+0%", "-10%", "+20%".
    """
    chosen = lang or detect_lang(text)
    voice = VOICE_BY_LANG.get(chosen, VOICE_BY_LANG["en"])
    audio = asyncio.run(_synthesize_async(text, voice, rate))
    if not audio:
        raise RuntimeError(
            f"Edge-TTS returned no audio for voice {voice}. "
            "This usually means the Microsoft endpoint rejected the content; "
            "try a shorter message or a different voice via TTS_VOICE_TH/EN env."
        )
    return audio
