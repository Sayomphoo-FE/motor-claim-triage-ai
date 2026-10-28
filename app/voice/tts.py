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


def _merge_mp3_chunks(chunks: list[bytes], pause_ms: int = 180) -> bytes:
    """Decode each MP3 chunk, append in order with a brief silence between,
    and re-encode as a single valid MP3.

    Why: Edge-TTS emits a full MP3 stream per call (ID3 header + frames).
    Concatenating the raw bytes gives an invalid "double-headed" file:
    some browsers (and Streamlit's bundled audio player) stop at the
    end-of-stream marker of the first chunk, which was the true cause
    of Thai responses appearing to be cut off after the first sentence.
    Round-tripping through pydub guarantees a single header + one
    continuous frame stream the player can walk from start to finish.
    """
    import io

    from pydub import AudioSegment

    non_empty = [c for c in chunks if c]
    if not non_empty:
        return b""
    if len(non_empty) == 1:
        return non_empty[0]

    combined = AudioSegment.empty()
    pause = AudioSegment.silent(duration=pause_ms)
    for i, raw in enumerate(non_empty):
        seg = AudioSegment.from_mp3(io.BytesIO(raw))
        combined += seg
        if i < len(non_empty) - 1:
            combined += pause

    out = io.BytesIO()
    combined.export(out, format="mp3")
    return out.getvalue()


async def _synthesize_async(text: str, voice: str, rate: str) -> bytes:
    """Synthesize sentence-by-sentence then merge properly.

    Splitting always (not just on failure) gives:
    - Robustness against Edge-TTS's "NoAudioReceived" bug on long
      mixed-script content — if one sentence fails we drop it instead
      of losing the whole message.
    - Deterministic sentence-level pacing via `_merge_mp3_chunks`,
      which decodes each chunk and inserts a short silence between.
    """
    normalised = _normalise(text)
    sentences = _split_sentences(normalised) or [normalised]

    chunks: list[bytes] = []
    for sentence in sentences:
        chunk = await _synthesize_chunk(sentence, voice, rate)
        if chunk:
            chunks.append(chunk)
    return _merge_mp3_chunks(chunks)


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
    sentences and the EN voice for English-only sentences. Merged into
    a single valid MP3 via `_merge_mp3_chunks` so browsers play it
    end-to-end without stopping at inter-sentence stream boundaries.
    """
    normalised = _normalise(text)
    sentences = _split_sentences(normalised) or [normalised]
    chunks: list[bytes] = []
    for sentence in sentences:
        voice = VOICE_BY_LANG["th"] if _THAI_CHARS_RE.search(sentence) else VOICE_BY_LANG["en"]
        chunk = await _synthesize_chunk(sentence, voice, rate)
        if chunk:
            chunks.append(chunk)
    return _merge_mp3_chunks(chunks)


def synthesize_mixed(text: str, rate: str = DEFAULT_RATE) -> bytes:
    """Synthesize text that mixes Thai and English, switching voice per
    sentence so each language is spoken by its native-voice."""
    audio = asyncio.run(_synthesize_mixed_async(text, rate))
    if not audio:
        raise RuntimeError("Edge-TTS returned no audio for the mixed-language text.")
    return audio
