"""Photo damage assessment via Claude vision.

Accepts one or more vehicle damage photos (JPEG / PNG) and returns a
short, factual damage description suitable for enriching a triage prompt.
Uses the same model as the triage agent so no extra API key is required.
"""
from __future__ import annotations

import base64
import os

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

_MODEL = os.getenv("TRIAGE_MODEL", "claude-sonnet-4-6")

_PROMPT = (
    "You are a motor vehicle damage assessor reviewing insurance claim photos. "
    "Describe the damage you can see: "
    "(1) which part of the vehicle is affected, "
    "(2) type of damage (dent, scratch, broken part, shattered glass, etc.), "
    "(3) apparent severity (cosmetic / minor / moderate / severe). "
    "Be factual and objective. Reply in English, 2–4 sentences."
)


def analyze_damage_photos(images: list[tuple[bytes, str]]) -> str:
    """Return a concise damage description from one or more photos.

    Args:
        images: list of (raw_bytes, mime_type) — e.g. (b"...", "image/jpeg")

    Returns:
        Damage description string, or empty string if images is empty.
    """
    if not images:
        return ""

    client = Anthropic()
    content: list[dict] = []

    for raw, mime in images:
        b64 = base64.standard_b64encode(raw).decode("utf-8")
        content.append({
            "type": "image",
            "source": {"type": "base64", "media_type": mime, "data": b64},
        })

    content.append({"type": "text", "text": _PROMPT})

    response = client.messages.create(
        model=_MODEL,
        max_tokens=400,
        messages=[{"role": "user", "content": content}],
    )
    return response.content[0].text.strip()
