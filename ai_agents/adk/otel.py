"""OpenTelemetry-shaped spans for the fleet path.

Exports to Cloud Trace when OTEL_EXPORTER_OTLP_ENDPOINT is set.
Always records an in-process timeline the UI and tests can read.
"""

from __future__ import annotations

import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Dict, Iterator, List, Optional

try:
    from opentelemetry import trace as otel_trace  # type: ignore

    _TRACER = otel_trace.get_tracer("verifleet")
except Exception:  # pragma: no cover - optional
    _TRACER = None


@dataclass
class SpanRecord:
    name: str
    started_at: float
    ended_at: Optional[float] = None
    attributes: Dict[str, Any] = field(default_factory=dict)
    status: str = "ok"
    error: Optional[str] = None

    def to_dict(self) -> dict:
        duration_ms = None
        if self.ended_at is not None:
            duration_ms = round((self.ended_at - self.started_at) * 1000, 2)
        return {
            "name": self.name,
            "status": self.status,
            "error": self.error,
            "duration_ms": duration_ms,
            "attributes": self.attributes,
        }


class SpanRecorder:
    def __init__(self) -> None:
        self.spans: List[SpanRecord] = []

    @contextmanager
    def span(self, name: str, **attributes: Any) -> Iterator[SpanRecord]:
        rec = SpanRecord(name=name, started_at=time.time(), attributes=dict(attributes))
        self.spans.append(rec)
        cm = _TRACER.start_as_current_span(name) if _TRACER is not None else None
        span_obj = cm.__enter__() if cm is not None else None
        try:
            yield rec
            rec.status = rec.status or "ok"
        except Exception as exc:
            rec.status = "error"
            rec.error = str(exc)
            if span_obj is not None:
                try:
                    span_obj.record_exception(exc)
                except Exception:
                    pass
            raise
        finally:
            rec.ended_at = time.time()
            if span_obj is not None:
                for k, v in rec.attributes.items():
                    try:
                        span_obj.set_attribute(k, v if isinstance(v, (str, int, float, bool)) else str(v))
                    except Exception:
                        pass
            if cm is not None:
                cm.__exit__(None, None, None)

    def timeline(self) -> List[dict]:
        return [s.to_dict() for s in self.spans]
