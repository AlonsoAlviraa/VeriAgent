"""ADK InMemoryRunner on a consult-only Agent.

Does not drive the four-child graph and never calls invoice.sign.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
from typing import Any, Dict

from .agents import build_consult_agent
from .config import GEMINI_MODEL, GOOGLE_AGENT_FRAMEWORK
from .consult import _safe_exc, parse_recommendation, skip_reason


def _empty(reason: str, runner: str = "none") -> Dict[str, Any]:
    return {
        "invoked": False,
        "model": GEMINI_MODEL,
        "framework": GOOGLE_AGENT_FRAMEWORK,
        "recommendation": None,
        "text": "",
        "reason": reason,
        "runner": runner,
        "events": 0,
        "consult_agent": "fiscal_fleet_consult",
    }


def _import_runner():
    try:
        from google.adk.runners import InMemoryRunner  # type: ignore

        return InMemoryRunner, "InMemoryRunner"
    except Exception:
        pass
    try:
        from google.adk.runners import Runner  # type: ignore

        return Runner, "Runner"
    except Exception as exc:
        raise ImportError(str(exc)) from exc


async def _drive(agent: Any, prompt: str) -> tuple[str, int]:
    RunnerCls, _name = _import_runner()
    try:
        runner = RunnerCls(agent=agent, app_name="verifleet")
    except TypeError:
        runner = RunnerCls(agent=agent)
    session_service = getattr(runner, "session_service", None)
    session_id = "fleet"
    if session_service is not None and hasattr(session_service, "create_session"):
        session = await session_service.create_session(app_name="verifleet", user_id="fleet")
        session_id = getattr(session, "id", None) or getattr(session, "session_id", "fleet")
    try:
        from google.genai import types  # type: ignore

        msg = types.Content(role="user", parts=[types.Part(text=prompt)])
    except Exception:
        msg = prompt
    text = ""
    events = 0
    agen = runner.run_async(user_id="fleet", session_id=session_id, new_message=msg)
    async for event in agen:
        events += 1
        content = getattr(event, "content", None)
        if not content:
            continue
        parts = getattr(content, "parts", None) or []
        chunk = "".join(getattr(p, "text", "") or "" for p in parts)
        if chunk.strip():
            text = chunk
    return text, events


def _run_sync(coro, timeout: float = 20.0) -> Any:
    try:
        asyncio.get_running_loop()
        running = True
    except RuntimeError:
        running = False
    if running:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(
                lambda: asyncio.run(asyncio.wait_for(coro, timeout=timeout))
            ).result(timeout=timeout + 2)
    return asyncio.run(asyncio.wait_for(coro, timeout=timeout))


def run_orchestrator(
    *,
    redacted_invoice: str,
    memory: dict,
    auditor_draft: str,
) -> Dict[str, Any]:
    blocked = skip_reason()
    if blocked:
        return _empty(blocked)

    agent = build_consult_agent()
    if agent is None:
        return _empty("adk_unavailable")

    prompt = (
        f"You are FiscalFleetOrchestrator ({GOOGLE_AGENT_FRAMEWORK}, {GEMINI_MODEL}). "
        "Background fiscal compliance. Do not chat. Do not invent hashes or XML. "
        "Do not call tools. "
        f"Auditor draft decision: {auditor_draft}\n"
        f"Tenant Memory Bank: {memory}\n"
        f"Invoice (PII redacted):\n{redacted_invoice[:2000]}\n"
        "Reply with exactly one of: SIGN, ESCALATE, REJECT — then one sentence why."
    )
    try:
        text, events = _run_sync(_drive(agent, prompt), timeout=20.0)
    except Exception as exc:
        return _empty(f"llm_error:{_safe_exc(exc)}")

    return {
        "invoked": True,
        "model": GEMINI_MODEL,
        "framework": GOOGLE_AGENT_FRAMEWORK,
        "recommendation": parse_recommendation(text or ""),
        "text": (text or "")[:800],
        "reason": "ok",
        "runner": "InMemoryRunner",
        "events": events,
        "consult_agent": "fiscal_fleet_consult",
    }
