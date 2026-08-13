"""Gemini 3.5 consult on the fleet path, with Grok fallback.

The model may *tighten* a SIGN into ESCALATE. It cannot open Armor,
override a math fail, or write a hash. No credentials → skip (tests).
XAI_API_KEY is enough to enable consult when Gemini is missing.
VERIFLEET_SKIP_LLM still skips (conftest).
"""

from __future__ import annotations

import os
import re
from typing import Any, Dict, Optional

from .config import GEMINI_MODEL, GOOGLE_AGENT_FRAMEWORK


def _gemini_configured() -> bool:
    return bool(
        os.getenv("GEMINI_API_KEY")
        or os.getenv("GOOGLE_API_KEY")
        or os.getenv("GOOGLE_CLOUD_PROJECT")
    )


def _xai_configured() -> bool:
    return bool(os.getenv("XAI_API_KEY"))


def skip_reason() -> Optional[str]:
    if os.getenv("VERIFLEET_SKIP_LLM", "").strip().lower() in {"1", "true", "yes"}:
        return "skip_llm"
    if not (_gemini_configured() or _xai_configured()):
        return "no_credentials"
    return None


def _enabled() -> bool:
    return skip_reason() is None


def parse_recommendation(text: str) -> Optional[str]:
    head = (text or "").strip().upper()
    for label in ("ESCALATE", "REJECT", "SIGN", "BLOCK"):
        if re.search(rf"\b{label}\b", head[:80]):
            if label == "REJECT":
                return "ESCALATE"
            if label == "BLOCK":
                return "BLOCK"
            if label == "SIGN":
                return "SIGN"
            return "ESCALATE"
    return None


_URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)
_SECRET_QS_RE = re.compile(r"(?i)(?:key|token|api[_-]?key)=[^\s&]+")


def _safe_exc(exc: BaseException) -> str:
    """Exception label without query strings, tokens, or key material."""
    return type(exc).__name__


def _safe_reason(raw: Any) -> str:
    """Drop URLs and key= query fragments from persisted consult reasons."""
    text = str(raw or "")
    text = _URL_RE.sub("[url]", text)
    text = _SECRET_QS_RE.sub("[redacted]", text)
    return text


def _consult_prompt(auditor_draft: str, memory: Dict[str, str], redacted_invoice: str, *, who: str) -> str:
    return (
        f"You are FiscalFleetOrchestrator ({who}). "
        "Background fiscal compliance. Do not chat. Do not invent hashes or XML.\n"
        f"Auditor draft decision: {auditor_draft}\n"
        f"Tenant Memory Bank: {memory}\n"
        f"Invoice (PII redacted):\n{redacted_invoice[:2000]}\n"
        "Reply with exactly one of: SIGN, ESCALATE, REJECT — then one sentence why."
    )


def _empty(*, model: str, framework: str, reason: str, runner: str) -> Dict[str, Any]:
    return {
        "invoked": False,
        "model": model,
        "framework": framework,
        "recommendation": None,
        "text": "",
        "reason": reason,
        "runner": runner,
        "consult_agent": "fiscal_fleet_consult",
    }


def _consult_grok(
    *,
    redacted_invoice: str,
    memory: Dict[str, str],
    auditor_draft: str,
) -> Dict[str, Any]:
    """Tighten-only consult via xAI Grok. Never raises into the hash path."""
    from ai_agents.xai_direct import DEFAULT_MODEL, chat_completion

    prompt = _consult_prompt(
        auditor_draft,
        memory,
        redacted_invoice,
        who=f"xai-direct, {DEFAULT_MODEL}",
    )
    try:
        text = chat_completion(
            [{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=256,
        )
    except Exception as exc:
        return _empty(
            model=DEFAULT_MODEL,
            framework="xai-direct",
            reason=f"grok_error:{_safe_exc(exc)}",
            runner="xai_direct",
        )
    if not (text or "").strip():
        return _empty(
            model=DEFAULT_MODEL,
            framework="xai-direct",
            reason="grok_empty",
            runner="xai_direct",
        )
    return {
        "invoked": True,
        "model": DEFAULT_MODEL,
        "framework": "xai-direct",
        "recommendation": parse_recommendation(text),
        "text": (text or "")[:800],
        "reason": "ok",
        "runner": "xai_direct",
        "consult_agent": "fiscal_fleet_consult",
    }


def consult(
    *,
    redacted_invoice: str,
    memory: Dict[str, str],
    auditor_draft: str,
    provider: Optional[str] = None,
) -> Dict[str, Any]:
    """Call Gemini 3.5, or Grok when Gemini is missing. Never raises into the hash path.

    ``provider`` may be ``gemini`` or ``grok`` to pin an A/B lane. The default
    auto path is unchanged. Neither lane can write a hash.
    """
    blocked = skip_reason()
    if blocked:
        return _empty(
            model=GEMINI_MODEL,
            framework=GOOGLE_AGENT_FRAMEWORK,
            reason=blocked,
            runner="none",
        )

    want = (provider or "").strip().lower()
    if want == "grok":
        if not _xai_configured():
            return _empty(
                model=GEMINI_MODEL,
                framework="xai-direct",
                reason="no_credentials",
                runner="none",
            )
        return _consult_grok(
            redacted_invoice=redacted_invoice,
            memory=memory,
            auditor_draft=auditor_draft,
        )
    if want == "gemini" and not _gemini_configured():
        return _empty(
            model=GEMINI_MODEL,
            framework=GOOGLE_AGENT_FRAMEWORK,
            reason="no_credentials",
            runner="none",
        )

    if not _gemini_configured():
        return _consult_grok(
            redacted_invoice=redacted_invoice,
            memory=memory,
            auditor_draft=auditor_draft,
        )

    from . import runner as adk_runner

    result = adk_runner.run_orchestrator(
        redacted_invoice=redacted_invoice,
        memory=memory,
        auditor_draft=auditor_draft,
    )
    if result.get("invoked") or result.get("reason") in {"no_credentials", "skip_llm"}:
        return result

    prompt = _consult_prompt(
        auditor_draft,
        memory,
        redacted_invoice,
        who=f"{GOOGLE_AGENT_FRAMEWORK}, {GEMINI_MODEL}",
    )
    try:
        text = _generate(prompt)
    except Exception as exc:
        result["reason"] = f"fallback_generate;{_safe_exc(exc)}"
        return result
    result["invoked"] = True
    result["text"] = (text or "")[:800]
    result["recommendation"] = parse_recommendation(text or "")
    result["runner"] = result.get("runner") or "none"
    result["reason"] = f"{_safe_reason(result.get('reason'))};fallback_generate"
    return result


def _generate(prompt: str) -> str:
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    try:
        from google import genai  # type: ignore

        kwargs = {}
        if api_key:
            kwargs["api_key"] = api_key
        client = genai.Client(**kwargs)
        resp = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
        return getattr(resp, "text", None) or ""
    except Exception:
        pass
    # REST fallback (same as gemini_direct, but 3.5 only).
    import requests

    if not api_key:
        raise RuntimeError("no Gemini API key for REST fallback")
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{GEMINI_MODEL}:generateContent"
    )
    r = requests.post(
        url,
        params={"key": api_key},
        json={"contents": [{"parts": [{"text": prompt}]}]},
        timeout=20,
    )
    r.raise_for_status()
    data = r.json()
    parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
    return "".join(p.get("text", "") for p in parts)
