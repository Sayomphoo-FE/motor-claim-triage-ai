"""Supervisor agent — minimal multi-agent orchestrator.

Design doc §5.1 and §5.3 describe this role: one entry point that
owns the conversation state and routes each turn to the right
specialist. In the current prototype the specialist list is:

    IntakeSpecialist   — collects the required fields via dialogue
                         (implementation: ConversationAgent)
    TriageSpecialist   — produces the policy-grounded recommendation
                         (implementation: TriageAgent)

A real deployment per the design doc would add InquirySpecialist,
SalesSpecialist, FraudEscalation, and MultiBrandRouter here; adding
one is roughly a 1-method change.

Why bother with a thin wrapper?
- The UI talks to **one** agent object regardless of which turn is
  which specialist. That decouples the UI from specialist churn.
- Every routing decision is appended to `state.supervisor_log`,
  giving auditors a flight recorder of "the supervisor chose X at
  turn N because Y".
- The decision point in `handle_user_turn` is the natural place to
  insert future intent classification before the intake path.
"""
from __future__ import annotations

from app.agents.conversation import (
    GREETING_COMBINED,
    ConversationAgent,
    ConversationState,
    ConversationStep,
    ConvLang,
)
from app.agents.triage import TriageAgent, TriageResult
from app.observability.call_log import save_call_log


class SupervisorAgent:
    """Entry point for the Call tab. Owns state; routes each turn."""

    def __init__(self) -> None:
        self.intake = ConversationAgent()

    # ---- Phase 1: scripted greeting ----------------------------------
    def start(self) -> ConversationState:
        """Create the state and queue the scripted bilingual greeting.

        Default conversation language is Thai (local market). The
        bilingual greeting still plays both introductions so a
        non-Thai-speaking caller can tell at once that the AI
        understands English; if they want to switch, they can simply
        reply in English and the LLM will handle the code-switch.
        """
        state = ConversationState(language="th")
        # lang="mixed" is a sentinel the UI uses to pick synthesize_mixed.
        state.append_assistant(GREETING_COMBINED, lang="mixed")
        state.log_decision(
            "intake", "greeting", "scripted TH+EN combined greeting (not LLM)"
        )
        state.log_decision(
            "intake", "set_language", "default = 'th' (local market)"
        )
        _persist(state)
        return state

    # ---- Phase 2: language choice ------------------------------------
    def set_language(self, state: ConversationState, language: ConvLang) -> None:
        """Available but no longer surfaced in the UI (default='th').
        Kept so a future UI can offer manual override."""
        state.language = language
        state.log_decision(
            "intake", "set_language", f"caller chose {language!r}"
        )
        _persist(state)

    # ---- Phase 3+: per-turn routing ----------------------------------
    def handle_user_turn(
        self, state: ConversationState, user_text: str, claim_id: str
    ) -> ConversationStep:
        """Append the user turn, decide what to do next, and perform it.

        Routing policy (prototype):
        - Always delegate first to the IntakeSpecialist, which returns
          either `action="ask"` or `action="triage"`.
        - On `action="triage"`, delegate to the TriageSpecialist. The
          resulting TriageResult is stored on the state.

        Returns the raw IntakeSpecialist step for display purposes.
        """
        state.append_user(user_text)

        step = self.intake.respond(state)
        state.collected = step.collected_info
        state.append_assistant(step.message_to_customer)
        state.log_decision(
            "intake",
            step.action,
            f"missing={step.missing_fields}; reasoning={step.reasoning[:120]}",
        )

        if step.action == "triage":
            state.log_decision(
                "triage",
                "run_triage",
                f"handing off to TriageAgent with claim_id={claim_id}",
            )
            state.triage = self._run_triage(state, claim_id)

        _persist(state)
        return step

    # ---- Internal ---------------------------------------------------
    def _run_triage(self, state: ConversationState, claim_id: str) -> TriageResult:
        return self.intake.run_triage(state, claim_id=claim_id)


def _persist(state: ConversationState) -> None:
    """Save the full call log; silence IO errors so the UI never blocks on
    disk problems during a live call."""
    try:
        save_call_log(state)
    except Exception:  # noqa: BLE001
        pass


# Convenience singleton import for the UI.
__all__ = ["SupervisorAgent"]
