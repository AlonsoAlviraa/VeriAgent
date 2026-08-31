"""
[AGENT-023] Cliente directo de xAI (Grok) SIN litellm.

Motivo: litellm requiere compilar una extensión Rust no disponible en este
entorno. xAI expone una API REST OpenAI-compatible, así que la llamamos directo
con `requests`. Filosofía zero-cost: usa los créditos gratuitos mensuales de xAI
($25/mes base + $150/mes con opt-in de data sharing).

Modelo por defecto: `grok-4.20-0309-non-reasoning` (el menos costoso de la
familia 4.x: sin cadena de razonamiento, más rápido y barato por token).

Interfaz compatible con llm_router.chat_completion():
    chat_completion(messages, temperature, max_tokens) -> str
"""

from __future__ import annotations

import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def _safe_log(text: object) -> str:
    from shared.redact import sanitize_log

    return sanitize_log(str(text) if text is not None else "")


def _load_dotenv() -> None:
    """Cargador ligero de .env sin dependencia de python-dotenv."""
    try:
        env_path = Path(__file__).resolve().parents[1] / ".env"
        if not env_path.exists():
            return
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k, v = k.strip(), v.strip().strip('"').strip("'")
            os.environ.setdefault(k, v)
    except Exception:
        pass


_load_dotenv()

# Modelo configurable vía XAI_MODEL. Default: non-reasoning (menos costoso).
# Para mayor calidad (más caro en créditos): XAI_MODEL=grok-4.20-0309-reasoning
DEFAULT_MODEL = os.getenv("XAI_MODEL", "grok-4.20-0309-non-reasoning")
XAI_BASE = "https://api.x.ai/v1/chat/completions"


def _get_api_key() -> Optional[str]:
    return os.getenv("XAI_API_KEY")


def chat_completion(
    messages: List[Dict[str, str]],
    temperature: float = 0.7,
    max_tokens: int = 4096,
    *,
    model: str = DEFAULT_MODEL,
    retries: int = 2,
) -> str:
    """
    Llama a la API de xAI (formato OpenAI-compatible). Drop-in del chat_completion.

    Retorna el texto generado, o "" si falla tras reintentos.
    """
    api_key = _get_api_key()
    if not api_key:
        logger.error("[xAI] XAI_API_KEY no configurada.")
        return ""

    payload: Dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    last_err = ""
    for attempt in range(retries + 1):
        try:
            import requests

            r = requests.post(
                XAI_BASE,
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json=payload,
                timeout=90,
            )
            if r.status_code == 200:
                data = r.json()
                choices = data.get("choices", [])
                if choices:
                    return choices[0].get("message", {}).get("content", "")
                return ""
            if r.status_code == 429:
                last_err = "429 rate limit"
                logger.warning("[xAI] Rate limit (429), reintentando…")
                time.sleep(2 ** attempt)
                continue
            if r.status_code in (500, 502, 503):
                last_err = f"{r.status_code} server error"
                time.sleep(2 ** attempt)
                continue
            # 402/403 = sin créditos o sin permiso (no recuperable).
            logger.error("[xAI] Error %s: %s", r.status_code, _safe_log(r.text[:300]))
            return ""
        except Exception as exc:
            last_err = _safe_log(exc)
            logger.warning("[xAI] Excepción: %s", last_err)
            time.sleep(2 ** attempt)

    logger.error("[xAI] Fallo tras reintentos: %s", _safe_log(last_err))
    return ""


def is_available() -> bool:
    """True si XAI_API_KEY está configurada."""
    return bool(_get_api_key())
