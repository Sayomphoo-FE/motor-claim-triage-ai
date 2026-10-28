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
    BRIDGE_TH_TO_EN,
    GREETING_EN,
    GREETING_TH,
    ConversationAgent,
    ConversationState,
    ConversationStep,
    ConvLang,
)
from app.agents.triage import TriageAgent, TriageResult


class SupervisorAgent:
    """Entry point for the Call tab. Owns state; routes each turn."""

    def __init__(self) -> None:
        self.intake = ConversationAgent()

    # ---- Phase 1: scripted greeting ----------------------------------
    def start(self) -> ConversationState:
        """Create the state and queue the scripted bilingual greeting.

        The greeting itself is not an LLM call — it's a static script
        (see docs/call_agent_playbook.md §1). The supervisor records
        this decision so the audit log is explicit about where the
        content came from.
        """
        state = ConversationState()
        state.append_assistant(GREETING_TH, lang="th")
        state.log_decision("intake", "greeting", "scripted TH greeting (not LLM)")

        state.append_assistant(BRIDGE_TH_TO_EN, lang="th")
        state.log_decision("intake", "greeting", "scripted TH→EN bridge")

        state.append_assistant(GREETING_EN, lang="en")
        state.log_decision("intake", "greeting", "scripted EN greeting (not LLM)")
        return state

    # ---- Phase 2: language choice ------------------------------------
    def set_language(self, state: ConversationState, language: ConvLang) -> None:
        """Called by the UI when the caller taps 🇹🇭 or 🇬🇧."""
        state.language = language
        state.log_decision(
            "intake", "set_language", f"caller chose {language!r}"
        )

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

        return step

    # ---- Internal ---------------------------------------------------
    def _run_triage(self, state: ConversationState, claim_id: str) -> TriageResult:
        return self.intake.run_triage(state, claim_id=claim_id)


# Convenience singleton import for the UI.
__all__ = ["SupervisorAgent"]
