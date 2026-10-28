"""Multi-turn claim-intake conversation agent.

Replaces the single-shot voice flow with a scripted-greeting +
checklist-driven dialogue. The AI opens the call with a fixed
intro (so greeting content is deterministic and reviewable), then
decides each turn whether it still needs more information or is
ready to hand the case to the triage agent.

Design decisions:
- Greeting is a *script*, not an LLM generation. This guarantees the
  compliance line ("I am an AI", "I will route you to a human") is
  always identical and auditable.
- Each turn the agent calls a single `respond` tool with action
  "ask" or "triage". We use one tool with an action discriminator
  rather than two tools because it is simpler to validate and
  Pydantic can enforce the shape in one place.
- When action="triage", we build a ClaimInput from the accumulated
  info and run the existing TriageAgent. The TriageAgent already
  carries the guardrails + audit log, so no duplication.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Literal

from anthropic import Anthropic
from dotenv import load_dotenv
from pydantic import BaseModel, Field

from app.agents.triage import TriageAgent, TriageResult
from app.schemas import ClaimInput

load_dotenv()

CONV_MODEL = os.getenv("CONVERSATION_MODEL", os.getenv("TRIAGE_MODEL", "claude-sonnet-4-6"))
PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "conversation.md"

ConvLang = Literal["th", "en"]

# ----------------------------------------------------------------------
# Scripted greetings
# ----------------------------------------------------------------------
BRAND_NAME = "ABC Insurance"

GREETING_TH_INTRO = (
    f"สวัสดีค่ะ ดิฉันคือ AI ผู้ช่วยรับเรื่องเคลมของ {BRAND_NAME} "
    "มีหน้าที่สอบถามข้อมูลเบื้องต้นแล้วส่งต่อให้เจ้าหน้าที่ "
    "ขอเรียนให้ทราบว่าดิฉันไม่ใช่ผู้ตัดสินใจอนุมัติ "
    "การตัดสินใจสุดท้ายทำโดยเจ้าหน้าที่เสมอค่ะ "
    "รบกวนเลือกภาษาที่ท่านสะดวกค่ะ"
)

GREETING_EN_INTRO = (
    f"Hello, I'm the AI claim intake assistant at {BRAND_NAME}. "
    "My job is to collect the initial details of your claim and pass them "
    "to a human officer. I am not the final decision maker — a human "
    "officer will make the final call. "
    "Please choose the language you prefer."
)

# Combined single-turn greeting played with mixed TH + EN voices.
# No prompt-to-speak at the end — the caller must pick a language first.
GREETING_COMBINED = f"{GREETING_TH_INTRO} {GREETING_EN_INTRO}"


# ----------------------------------------------------------------------
# Required information checklist
# ----------------------------------------------------------------------
REQUIRED_FIELDS: list[tuple[str, str]] = [
    ("vehicle", "Vehicle make/model/year"),
    ("incident_date", "Date of the incident"),
    ("claim_description", "What happened (free-text description)"),
    ("documents_submitted", "Documents already submitted"),
    ("customer_claim_history", "Claim history in the past 12–24 months"),
]

REQUIRED_FIELD_KEYS = [k for k, _ in REQUIRED_FIELDS]


# ----------------------------------------------------------------------
# Collected info + conversation step
# ----------------------------------------------------------------------
class CollectedInfo(BaseModel):
    vehicle: str = ""
    incident_date: str = ""  # ISO or free-text, triage agent will coerce
    claim_description: str = ""
    documents_submitted: list[str] = Field(default_factory=list)
    customer_claim_history: str = ""


class ConversationStep(BaseModel):
    """One LLM turn in the intake conversation."""

    action: Literal["ask", "triage"]
    message_to_customer: str
    collected_info: CollectedInfo
    missing_fields: list[str] = Field(default_factory=list)
    reasoning: str = ""


# Tool schema given to Claude; mirrors ConversationStep.
CONVERSATION_TOOL = {
    "name": "respond",
    "description": (
        "Decide the next action in the claim intake conversation. "
        "Call this exactly once per turn."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["ask", "triage"],
                "description": (
                    "'ask' = need more info, speak message_to_customer and wait. "
                    "'triage' = have enough info, speak message_to_customer as a "
                    "handover line, then run the triage agent."
                ),
            },
            "message_to_customer": {
                "type": "string",
                "description": (
                    "What the AI should say to the customer this turn. "
                    "Natural single-sentence Thai or English, matching the "
                    "conversation language."
                ),
            },
            "collected_info": {
                "type": "object",
                "properties": {
                    "vehicle": {"type": "string"},
                    "incident_date": {
                        "type": "string",
                        "description": "ISO 8601 if possible, otherwise verbatim.",
                    },
                    "claim_description": {"type": "string"},
                    "documents_submitted": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "customer_claim_history": {"type": "string"},
                },
                "required": [
                    "vehicle",
                    "incident_date",
                    "claim_description",
                    "documents_submitted",
                    "customer_claim_history",
                ],
            },
            "missing_fields": {
                "type": "array",
                "items": {"type": "string"},
                "description": (
                    "Subset of required fields still missing. "
                    "Must be empty when action='triage'."
                ),
            },
            "reasoning": {
                "type": "string",
                "description": "One-sentence private reasoning for the chosen action.",
            },
        },
        "required": [
            "action",
            "message_to_customer",
            "collected_info",
            "missing_fields",
            "reasoning",
        ],
    },
}


# ----------------------------------------------------------------------
# Conversation agent
# ----------------------------------------------------------------------
TurnLang = Literal["th", "en", "mixed"]


@dataclass
class Turn:
    role: Literal["assistant", "user"]
    text: str
    # "th"/"en" use single-voice TTS; "mixed" uses synthesize_mixed; None =
    # fall back to detect_lang from text.
    lang: TurnLang | None = None


@dataclass
class SupervisorDecision:
    """One supervisor routing decision — kept so audit can show which
    specialist handled which turn."""

    turn_index: int
    specialist: Literal["intake", "triage"]
    action: str  # "ask", "triage", "greeting", "set_language"
    note: str = ""


def _default_session_id() -> str:
    # Lazy import so the module stays importable without touching the
    # call-log module (and its env/filesystem assumptions) at import time.
    from app.observability.call_log import new_session_id

    return new_session_id()


@dataclass
class ConversationState:
    language: ConvLang | None = None  # None = still awaiting customer's choice
    turns: list[Turn] = field(default_factory=list)
    collected: CollectedInfo = field(default_factory=CollectedInfo)
    triage: TriageResult | None = None
    processing: bool = False  # True while we are between user send and AI response
    supervisor_log: list[SupervisorDecision] = field(default_factory=list)
    session_id: str = field(default_factory=_default_session_id)
    started_at: datetime = field(default_factory=datetime.now)

    def append_user(self, text: str) -> None:
        self.turns.append(Turn(role="user", text=text, lang=self.language))

    def append_assistant(self, text: str, lang: TurnLang | None = None) -> None:
        self.turns.append(Turn(role="assistant", text=text, lang=lang or self.language))

    def log_decision(
        self, specialist: Literal["intake", "triage"], action: str, note: str = ""
    ) -> None:
        self.supervisor_log.append(
            SupervisorDecision(
                turn_index=len(self.turns),
                specialist=specialist,
                action=action,
                note=note,
            )
        )


class ConversationAgent:
    def __init__(self, model: str = CONV_MODEL):
        self.client = Anthropic()
        self.model = model

    def start(self) -> ConversationState:
        """Return initial state with BOTH the Thai and English scripted greetings
        queued, so the caller can hear each and then pick a language.

        state.language stays None until the UI records the caller's choice.
        """
        state = ConversationState(language=None)
        state.append_assistant(GREETING_TH, lang="th")
        state.append_assistant(BRIDGE_TH_TO_EN, lang="th")
        state.append_assistant(GREETING_EN, lang="en")
        return state

    def set_language(self, state: ConversationState, language: ConvLang) -> None:
        """Lock the language for the rest of the call."""
        state.language = language

    def respond(self, state: ConversationState) -> ConversationStep:
        """Decide the next assistant action based on the full history."""
        prompt = self._render_prompt(state)
        response = self.client.messages.create(
            model=self.model,
            max_tokens=800,
            tools=[CONVERSATION_TOOL],
            tool_choice={"type": "tool", "name": "respond"},
            messages=[{"role": "user", "content": prompt}],
        )
        tool_block = next(
            b for b in response.content if getattr(b, "type", None) == "tool_use"
        )
        payload = (
            tool_block.input
            if isinstance(tool_block.input, dict)
            else json.loads(tool_block.input)
        )
        return ConversationStep.model_validate(payload)

    def run_triage(self, state: ConversationState, claim_id: str) -> TriageResult:
        """Convert collected info into a ClaimInput and run full triage."""
        incident = _parse_iso_date(state.collected.incident_date)
        today = date.today()
        claim = ClaimInput(
            claim_id=claim_id,
            customer="Voice caller (anonymous)",
            vehicle=state.collected.vehicle or "(unspecified)",
            incident_date=incident,
            claim_submitted_date=today,
            claim_description=state.collected.claim_description or "(not provided)",
            documents_submitted=state.collected.documents_submitted or [],
            customer_claim_history=state.collected.customer_claim_history or "(unknown)",
            response_language=state.language,
        )
        agent = TriageAgent()
        return agent.run(claim)

    def _render_prompt(self, state: ConversationState) -> str:
        template = PROMPT_PATH.read_text(encoding="utf-8")
        transcript = "\n".join(
            f"[{t.role}]: {t.text}" for t in state.turns
        ) or "(no turns yet)"
        checklist = "\n".join(f"- {k}: {desc}" for k, desc in REQUIRED_FIELDS)
        return template.format(
            conversation_language=state.language,
            required_fields=checklist,
            transcript=transcript,
            collected_so_far=state.collected.model_dump_json(indent=2),
        )


def _parse_iso_date(s: str) -> date:
    """Best-effort date parse; fall back to today for the prototype."""
    try:
        return date.fromisoformat(s[:10])
    except Exception:  # noqa: BLE001
        return date.today()
