"""ADK agent definitions.

google-adk is imported when installed. Tests and offline runs use the
deterministic runtime; this module still constructs the same four agents
so the repo proves Architectural Discipline + the mandatory framework.
"""

from __future__ import annotations

from typing import Any, Optional

from .config import GEMINI_MODEL, GOOGLE_AGENT_FRAMEWORK

ADK_AVAILABLE = False
_ADK_IMPORT_ERROR: Optional[str] = None

try:
    from google.adk.agents import Agent  # type: ignore

    ADK_AVAILABLE = True
except Exception as exc:  # pragma: no cover
    Agent = None  # type: ignore
    _ADK_IMPORT_ERROR = str(exc)


def _instruction(role: str, rules: str) -> str:
    return (
        f"You are {role} in VeriFleet, a Spanish VeriFactu compliance fleet. "
        "You operate in the background. Do not chat. Call tools. "
        "Never invent a hash, XML, or AEAT CSV. "
        f"{rules}"
    )


def build_adk_root() -> Any:
    """Build the ADK FiscalFleetOrchestrator with four sub-agents.

    Returns None when google-adk is not installed. The runtime still runs.
    """
    if not ADK_AVAILABLE or Agent is None:
        return None

    ingestion = Agent(
        name="ingestion_agent",
        model=GEMINI_MODEL,
        description="Extract invoice fields from documents.",
        instruction=_instruction(
            "IngestionAgent",
            "Extract issuer, customer, lines, taxes, totals. "
            "If OCR confidence is low, mark fields uncertain. Never sign.",
        ),
    )
    auditor = Agent(
        name="fiscal_auditor_agent",
        model=GEMINI_MODEL,
        description="Audit math, NIF, and tenant policy.",
        instruction=_instruction(
            "FiscalAuditorAgent",
            "PASS only if Base+IVA=Total (±0.01), NIFs validate, and Memory Bank "
            "does not deny the category. Otherwise ESCALATE. Never call invoice.sign.",
        ),
    )
    signer = Agent(
        name="signer_agent",
        model=GEMINI_MODEL,
        description="Delegate create/sign to core_engine.",
        instruction=_instruction(
            "SignerAgent",
            "Call invoice.create then invoice.sign only after auditor PASS. "
            "The core engine computes the hash. You do not.",
        ),
    )
    escalation = Agent(
        name="escalation_agent",
        model=GEMINI_MODEL,
        description="Human review queue.",
        instruction=_instruction(
            "EscalationAgent",
            "Record why the invoice was not signed. Never call invoice.sign.",
        ),
    )
    return Agent(
        name="fiscal_fleet_orchestrator",
        model=GEMINI_MODEL,
        description="Background VeriFactu fleet orchestrator.",
        instruction=_instruction(
            "FiscalFleetOrchestrator",
            "Delegate ingestion → auditor → signer or escalation. "
            "Do not skip the auditor. Do not talk to the user mid-flight.",
        ),
        sub_agents=[ingestion, auditor, signer, escalation],
    )


def build_consult_agent() -> Any:
    """Single Agent, no sub_agents, no tools. Same job as consult()."""
    if not ADK_AVAILABLE or Agent is None:
        return None
    return Agent(
        name="fiscal_fleet_consult",
        model=GEMINI_MODEL,
        description="Tighten-only consult after the deterministic auditor.",
        instruction=(
            f"You are FiscalFleetOrchestrator ({GOOGLE_AGENT_FRAMEWORK}, {GEMINI_MODEL}). "
            "Background fiscal compliance. Do not chat. Do not invent hashes or XML. "
            "Do not call tools. Reply with exactly one of: SIGN, ESCALATE, REJECT — then one sentence why."
        ),
    )


def adk_status() -> dict:
    return {
        "framework": "google-adk",
        "available": ADK_AVAILABLE,
        "model": GEMINI_MODEL,
        "import_error": _ADK_IMPORT_ERROR,
        "runner": "InMemoryRunner",
        "consult_agent": "fiscal_fleet_consult",
    }
