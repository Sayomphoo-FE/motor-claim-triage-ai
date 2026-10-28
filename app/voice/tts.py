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
    """Split on Thai + English sentence terminators, preserving them.

    The previous implementation used a character class
    ``[\\.\\?!。ค่ะคะครับนะคะนะครับ]`` which actually matches each
    individual Thai letter (ค, ะ, ร, ั, บ, น), not the words
    "ค่ะ"/"ครับ". That over-split the greeting into fragments
    Edge-TTS could not synthesise, so whole sentences silently
    disappeared from the output. The fix matches sentence-end
    markers as proper alternatives.
    """
    import re

    text = text.strip()
    if not text:
        return []

    # Match an end-of-sentence marker that is followed by whitespace or
    # the end of the string. We iterate matches instead of using re.split
    # because the TH particles are multi-character and only variable-
    # width lookbehind (unsupported in `re`) would let us split cleanly.
    end_re = re.compile(r"(?:[\.\?!。]|ค่ะ|คะ|ครับ|นะคะ|นะครับ)(?=\s|$)")

    sentences: list[str] = []
    last = 0
    for m in end_re.finditer(text):
        end = m.end()
        chunk = text[last:end].strip()
        if chunk:
            sentences.append(chunk)
        last = end
    tail = text[last:].strip()
    if tail:
        sentences.append(tail)
    return sentences


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


async def _synthesize_mixed_async(text: str, rate: str) -> bytes:
    """Synthesize bilingual text, using the TH voice for Thai-containing
    sentences and the EN voice for English-only sentences. Concatenate
    the MP3 bytes so the caller hears one continuous stream.
    """
    normalised = _normalise(text)
    sentences = _split_sentences(normalised) or [normalised]
    out = bytearray()
    for sentence in sentences:
        voice = VOICE_BY_LANG["th"] if _THAI_CHARS_RE.search(sentence) else VOICE_BY_LANG["en"]
        chunk = await _synthesize_chunk(sentence, voice, rate)
        if chunk:
            out.extend(chunk)
    return bytes(out)


def synthesize_mixed(text: str, rate: str = DEFAULT_RATE) -> bytes:
    """Synthesize text that mixes Thai and English, switching voice per
    sentence so each language is spoken by its native-voice."""
    audio = asyncio.run(_synthesize_mixed_async(text, rate))
    if not audio:
        raise RuntimeError("Edge-TTS returned no audio for the mixed-language text.")
    return audio
