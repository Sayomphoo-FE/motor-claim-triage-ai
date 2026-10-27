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

DEFAULT_RATE = os.getenv("TTS_RATE", "+0%")  # slower → "-10%", faster → "+15%"


_THAI_CHARS_RE = re.compile(r"[฀-๿]")


def detect_lang(text: str) -> str:
    """Trivial Thai vs English detector based on Unicode range."""
    return "th" if _THAI_CHARS_RE.search(text) else "en"


async def _synthesize_async(text: str, voice: str, rate: str) -> bytes:
    import edge_tts

    buf = bytearray()
    communicate = edge_tts.Communicate(text, voice=voice, rate=rate)
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            buf.extend(chunk["data"])
    return bytes(buf)


def synthesize(text: str, lang: str | None = None, rate: str = DEFAULT_RATE) -> bytes:
    """Synthesize text to MP3 audio bytes.

    Args:
        text: free-text content.
        lang: "th", "en", or None to auto-detect from text.
        rate: Edge-TTS rate string, e.g. "+0%", "-10%", "+20%".
    """
    chosen = lang or detect_lang(text)
    voice = VOICE_BY_LANG.get(chosen, VOICE_BY_LANG["en"])
    return asyncio.run(_synthesize_async(text, voice, rate))
