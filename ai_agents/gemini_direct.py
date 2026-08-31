"""
[AGENT-022] Cliente directo de Gemini (Google AI Studio) SIN litellm.

Motivo: litellm requiere compilar una extensión Rust (Cargo) que no está
disponible en entornos Windows sin toolchain. Este cliente llama a la REST API
oficial de Gemini directamente con `requests`, manteniendo la filosofía zero-cost
(sin tarjeta) y siendo drop-in compatible con el router del repositorio.

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
    """Cargador ligero de .env sin dependencia de python-dotenv.

    Busca el .env en el directorio del proyecto (2 niveles arriba de este
    módulo: ai_agents/gemini_direct.py → raíz del repo).
    """
    try:
        # ai_agents/gemini_direct.py → parents[1] es la raíz del repo.
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

DEFAULT_MODEL = "gemini-2.0-flash"
GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta/models"


def _get_api_key() -> Optional[str]:
    return os.getenv("GEMINI_API_KEY")


def chat_completion(
    messages: List[Dict[str, str]],
    temperature: float = 0.7,
    max_tokens: int = 4096,
    *,
    model: str = DEFAULT_MODEL,
    retries: int = 2,
) -> str:
    """
    Llama a Gemini REST API. Drop-in del chat_completion de llm_router.

    Mapea messages (rol system/user/assistant) al formato contents de Gemini.
    Retorna el texto generado, o "" si falla tras reintentos.
    """
    api_key = _get_api_key()
    if not api_key:
        logger.error("[Gemini] GEMINI_API_KEY no configurada.")
        return ""

    # Gemini separa system_instruction del contents.
    system_text = ""
    contents: List[Dict[str, Any]] = []
    for m in messages:
        role = m.get("role", "user")
        text = m.get("content", "")
        if role == "system":
            system_text += (text + "\n")
        else:
            # Gemini usa roles "user" y "model".
            gemini_role = "model" if role == "assistant" else "user"
            contents.append({"role": gemini_role, "parts": [{"text": text}]})

    payload: Dict[str, Any] = {
        "contents": contents,
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_tokens,
        },
    }
    if system_text.strip():
        payload["systemInstruction"] = {"parts": [{"text": system_text.strip()}]}

    url = f"{GEMINI_BASE}/{model}:generateContent"

    last_err = ""
    for attempt in range(retries + 1):
        try:
            import requests

            r = requests.post(
                url,
                params={"key": api_key},
                json=payload,
                timeout=60,
            )
            if r.status_code == 200:
                data = r.json()
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    return "".join(p.get("text", "") for p in parts)
                # Respuesta vacía (p.ej. bloqueo de seguridad).
                return ""
            if r.status_code == 429:
                # Rate limit: backoff y reintento.
                last_err = "429 rate limit"
                logger.warning("[Gemini] Rate limit (429), reintentando…")
                time.sleep(2 ** attempt)
                continue
            if r.status_code in (500, 502, 503):
                last_err = f"{r.status_code} server error"
                time.sleep(2 ** attempt)
                continue
            # Error de cliente no recuperable (400, 401, 403, 404).
            logger.error("[Gemini] Error %s: %s", r.status_code, _safe_log(r.text[:300]))
            return ""
        except Exception as exc:
            last_err = _safe_log(exc)
            logger.warning("[Gemini] Excepción: %s", last_err)
            time.sleep(2 ** attempt)

    logger.error("[Gemini] Fallo tras reintentos: %s", _safe_log(last_err))
    return ""


def is_available() -> bool:
    """True si GEMINI_API_KEY está configurada."""
    return bool(_get_api_key())
