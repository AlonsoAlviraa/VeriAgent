"""VeriFleet: Google ADK fiscal-compliance agent fleet.

This package is the All Things Agentic product path. CrewAI stays unused here.
"""

from .config import GEMINI_MODEL, GOOGLE_AGENT_FRAMEWORK
from .runtime import run_fleet

__all__ = ["GEMINI_MODEL", "GOOGLE_AGENT_FRAMEWORK", "run_fleet"]
