"""FiscalFleetOrchestrator entry — ADK root agent used by Cloud Run / adk web."""

from __future__ import annotations

from .agents import build_adk_root
from .config import GEMINI_MODEL

# google-adk discovers `root_agent` when this module is the agent package.
root_agent = build_adk_root()

__all__ = ["root_agent", "GEMINI_MODEL"]
