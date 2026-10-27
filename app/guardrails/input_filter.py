"""Input guardrail: PII masking + prompt-injection detection.

Policy for this prototype:
- PII that leaks into free-text (phone, Thai national ID, licence plate)
  is masked BEFORE the LLM sees it. The audit log stores both the
  original and masked versions so an officer can still see the raw
  data for case handling, but the LLM only ever receives the mask.
- Prompt-injection patterns are *flagged* (not blocked) so the agent
  can decide to escalate to a human. We lean toward surfacing rather
  than hard-blocking because false positives hurt real customers.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Final

PHONE_RE: Final = re.compile(r"\b(?:0\d{1,2}[-\s]?\d{3}[-\s]?\d{4}|\+66\d{9})\b")
# Thai national ID = 13 digits, usually formatted X-XXXX-XXXXX-XX-X.
THAI_ID_RE: Final = re.compile(r"\b\d[-\s]?\d{4}[-\s]?\d{5}[-\s]?\d{2}[-\s]?\d\b")
# Loose Thai plate pattern: 1-2 letters + 1-4 digits (English transliteration).
PLATE_RE: Final = re.compile(r"\b[A-Z]{1,2}[-\s]?\d{1,4}\b")
EMAIL_RE: Final = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")

INJECTION_PATTERNS: Final = [
    r"ignore (all|previous|the above) (instructions?|prompts?|rules?)",
    r"disregard (the )?(system|previous) prompt",
    r"you are now ",
    r"from now on,? (act|behave|respond) as",
    r"approve (my|this) claim",
    r"force (routing|coverage) to",
    r"reveal (your|the) (system )?prompt",
    r"what are your (instructions|rules|guidelines)",
]
_INJECTION_RE = re.compile("|".join(INJECTION_PATTERNS), re.IGNORECASE)


@dataclass
class InputGuardResult:
    sanitized: str
    pii_triggers: list[str] = field(default_factory=list)
    injection_triggers: list[str] = field(default_factory=list)

    @property
    def had_pii(self) -> bool:
        return bool(self.pii_triggers)

    @property
    def had_injection(self) -> bool:
        return bool(self.injection_triggers)


def _mask(pattern: re.Pattern[str], label: str, text: str, triggers: list[str]) -> str:
    def repl(m: re.Match[str]) -> str:
        triggers.append(f"{label}:{m.group(0)}")
        return f"[REDACTED-{label}]"

    return pattern.sub(repl, text)


def sanitize_text(text: str) -> InputGuardResult:
    """Run PII mask + injection detection on a single string."""
    pii_triggers: list[str] = []
    out = text
    out = _mask(THAI_ID_RE, "ID", out, pii_triggers)
    out = _mask(PHONE_RE, "PHONE", out, pii_triggers)
    out = _mask(EMAIL_RE, "EMAIL", out, pii_triggers)
    out = _mask(PLATE_RE, "PLATE", out, pii_triggers)

    injection_triggers = sorted({m.group(0).lower() for m in _INJECTION_RE.finditer(out)})

    return InputGuardResult(
        sanitized=out,
        pii_triggers=pii_triggers,
        injection_triggers=injection_triggers,
    )
