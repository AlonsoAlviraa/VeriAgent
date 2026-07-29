"""
[CORE-011 / PUX-03] Lifecycle webhook / event emission with durable outbox.

Dos modos:
1. In-memory (default, sin DB): sink en proceso para tests/observabilidad +
   POST opcional a WEBHOOK_URL. Fire-and-forget, como antes.
2. Durable (con DB): pattern outbox. Cada evento se persiste como entrega
   PENDING contra las suscripciones activas del tenant. Un worker procesa la
   cola con reintentos de backoff exponencial y marca DEAD_LETTER tras
   max_attempts fallos.

El modo durable se activa automáticamente cuando el emitter se construye con
una sesión de DB (como hace InvoiceService).
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

# Process-local sink for tests/observability (events only — not invoice chain tips)
_EVENT_LOG: List[Dict[str, Any]] = []
_LOCK = threading.Lock()
_HANDLERS: List[Callable[[str, Dict[str, Any]], None]] = []

# Backoff exponencial: 1s, 2s, 4s, 8s, 16s… tope 5 min.
_BACKOFF_BASE_SECONDS = 1
_BACKOFF_MAX_SECONDS = 300
HTTP_TIMEOUT_SECONDS = 5


def clear_event_log() -> None:
    with _LOCK:
        _EVENT_LOG.clear()


def get_event_log() -> List[Dict[str, Any]]:
    with _LOCK:
        return list(_EVENT_LOG)


def register_handler(fn: Callable[[str, Dict[str, Any]], None]) -> None:
    _HANDLERS.append(fn)


def _sign_payload(payload: bytes, secret: str) -> str:
    """HMAC-SHA256 del payload con el secreto de la suscripción."""
    return hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()


def _compute_backoff(attempts: int) -> datetime:
    """Próximo intento con backoff exponencial topeado."""
    delay = min(_BACKOFF_MAX_SECONDS, _BACKOFF_BASE_SECONDS * (2 ** max(0, attempts - 1)))
    return datetime.now(timezone.utc) + timedelta(seconds=delay)


class WebhookEmitter:
    """Emisor de eventos de ciclo de vida (in-memory o durable outbox)."""

    def __init__(self, db=None):
        self.db = db
        self.url = os.getenv("WEBHOOK_URL")

    def emit(self, event: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Emite un evento. Si hay DB, persiste entregas en el outbox por suscripción
        activa. Siempre alimenta el log en memoria + handlers + WEBHOOK_URL.
        """
        record = {"event": event, "payload": payload}
        with _LOCK:
            _EVENT_LOG.append(record)
        for h in list(_HANDLERS):
            try:
                h(event, payload)
            except Exception as exc:
                logger.warning("webhook handler error: %s", exc)

        # Modo durable: encolar entregas a las suscripciones activas del tenant.
        if self.db is not None:
            try:
                self._enqueue_deliveries(event, payload, payload.get("tenant_id"))
            except Exception as exc:
                logger.warning("webhook outbox enqueue failed: %s", exc)

        # Fire-and-forget al WEBHOOK_URL global (compatibilidad hacia atrás).
        if self.url:
            try:
                import requests

                requests.post(
                    self.url,
                    data=json.dumps(record),
                    headers={"Content-Type": "application/json"},
                    timeout=3,
                )
            except Exception as exc:
                logger.warning("webhook POST failed: %s", exc)
        return record

    # ------------------------------------------------------------------
    # Durable outbox
    # ------------------------------------------------------------------
    def _enqueue_deliveries(self, event: str, payload: Dict[str, Any], tenant_id: Optional[str]) -> None:
        """Crea filas PENDING en webhook_deliveries para cada suscripción matching."""
        from core_engine.control_plane.models import (
            WebhookDeliveryModel,
            WebhookSubscriptionModel,
        )

        if tenant_id is None:
            return
        subs = (
            self.db.query(WebhookSubscriptionModel)
            .filter(
                WebhookSubscriptionModel.tenant_id == tenant_id,
                WebhookSubscriptionModel.active.is_(True),
            )
            .all()
        )
        now = datetime.now(timezone.utc)
        for sub in subs:
            events = sub.events or []
            # events vacío = suscrito a todo.
            if events and event not in events:
                continue
            self.db.add(WebhookDeliveryModel(
                subscription_id=sub.id,
                event=event,
                payload=payload,
                status="PENDING",
                attempts=0,
                max_attempts=5,
                next_attempt_at=now,
            ))
        self.db.commit()

    def process_pending(self, max_items: int = 50) -> Dict[str, int]:
        """
        Worker: procesa entregas PENDING/RETRY vencidas.

        Returns:
            {"delivered": n, "retried": n, "dead_lettered": n, "errors": n}
        """
        if self.db is None:
            return {"delivered": 0, "retried": 0, "dead_lettered": 0, "errors": 0}

        from core_engine.control_plane.models import (
            WebhookDeliveryModel,
            WebhookSubscriptionModel,
        )

        now = datetime.now(timezone.utc)
        pending = (
            self.db.query(WebhookDeliveryModel)
            .filter(
                WebhookDeliveryModel.status.in_(["PENDING", "RETRY"]),
                WebhookDeliveryModel.next_attempt_at.is_(None)
                | (WebhookDeliveryModel.next_attempt_at <= now),
            )
            .order_by(WebhookDeliveryModel.created_at)
            .limit(max_items)
            .all()
        )

        stats = {"delivered": 0, "retried": 0, "dead_lettered": 0, "errors": 0}
        for delivery in pending:
            sub = self.db.get(WebhookSubscriptionModel, delivery.subscription_id)
            if sub is None or not sub.active:
                delivery.status = "DEAD_LETTER"
                delivery.last_error = "subscription gone or inactive"
                stats["dead_lettered"] += 1
                continue

            ok, err = _deliver_once(sub.url, sub.secret, delivery.event, delivery.payload)
            delivery.attempts += 1
            if ok:
                delivery.status = "DELIVERED"
                delivery.delivered_at = datetime.now(timezone.utc)
                delivery.last_error = None
                stats["delivered"] += 1
            else:
                stats["errors"] += 1
                delivery.last_error = (err or "")[:500]
                if delivery.attempts >= delivery.max_attempts:
                    delivery.status = "DEAD_LETTER"
                    stats["dead_lettered"] += 1
                else:
                    delivery.status = "RETRY"
                    delivery.next_attempt_at = _compute_backoff(delivery.attempts)
                    stats["retried"] += 1
        self.db.commit()
        return stats


def _deliver_once(url: str, secret: Optional[str], event: str, payload: Dict[str, Any]) -> tuple:
    """Envía una entrega HTTP. Returns (ok: bool, error: str|None)."""
    import requests

    body = json.dumps({"event": event, "payload": payload}).encode("utf-8")
    headers = {"Content-Type": "application/json", "X-VeriAgent-Event": event}
    if secret:
        headers["X-VeriAgent-Signature"] = _sign_payload(body, secret)
    try:
        resp = requests.post(url, data=body, headers=headers, timeout=HTTP_TIMEOUT_SECONDS)
        if 200 <= resp.status_code < 300:
            return True, None
        return False, f"HTTP {resp.status_code}: {resp.text[:200]}"
    except Exception as exc:
        return False, str(exc)
