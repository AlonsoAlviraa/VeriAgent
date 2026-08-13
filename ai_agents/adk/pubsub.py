"""Pub/Sub adapter. No-op unless PUBSUB_TOPIC is set (local tests stay silent)."""

from __future__ import annotations

import json
import os
from typing import Any, Dict


def topic_name() -> str:
    return (os.getenv("PUBSUB_TOPIC") or "").strip()


def publish(event: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    topic = topic_name()
    if not topic:
        return {"published": False, "reason": "PUBSUB_TOPIC unset"}
    body = json.dumps({"event": event, **payload}, default=str).encode("utf-8")
    try:
        from google.cloud import pubsub_v1  # type: ignore

        publisher = pubsub_v1.PublisherClient()
        future = publisher.publish(topic, body, event=event)
        return {
            "published": True,
            "topic": topic,
            "message_id": str(future.result(timeout=8)),
        }
    except Exception as exc:
        return {"published": False, "topic": topic, "reason": str(exc)}


def unwrap_push(body: Dict[str, Any]) -> Dict[str, Any]:
    """Decode a Cloud Pub/Sub push envelope or a raw fleet payload."""
    if isinstance(body.get("invoice"), dict) or body.get("raw_text") or body.get("file_id"):
        return body
    message = body.get("message") or {}
    data = message.get("data")
    if not data:
        return body
    import base64

    raw = base64.b64decode(data).decode("utf-8")
    return json.loads(raw)
