"""
[AGENT-020 / Sprint 5-V2] Job store + async runner para el grafo vía API.

Cola de jobs en memoria (suficiente para MVP single-node; en prod se mueve a
Redis/Celery). Permite disparar el grafo de forma asíncrona desde un endpoint
FastAPI y consultar estado/resultado por job_id.

Estados de un job:
    pending → running → done | failed | budget_exceeded
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from ai_agents.graphs.cost_guard import DEFAULT_TOKEN_BUDGET, budgeted_run

logger = logging.getLogger(__name__)


@dataclass
class GraphJob:
    """Estado de un job de ejecución del grafo."""
    id: str
    goal: str
    prompt: str
    status: str = "pending"  # pending|running|done|failed|budget_exceeded
    created_at: str = ""
    finished_at: str = ""
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        # No exponer blobs grandes en listados; el resultado se pide aparte.
        return d


class GraphJobStore:
    """Job store en memoria thread-safe."""

    def __init__(self):
        self._jobs: Dict[str, GraphJob] = {}
        self._lock = threading.Lock()

    def submit(
        self,
        goal: str,
        prompt: str,
        *,
        budget: int = DEFAULT_TOKEN_BUDGET,
        max_iterations: int = 6,
        background: bool = True,
    ) -> GraphJob:
        """
        Crea y (opcionalmente) ejecuta un job.

        Args:
            background: si True, ejecuta en un thread daemon (no bloquea).
        """
        job = GraphJob(
            id=str(uuid.uuid4()),
            goal=goal,
            prompt=prompt,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        with self._lock:
            self._jobs[job.id] = job

        if background:
            t = threading.Thread(
                target=self._run, args=(job.id, budget, max_iterations),
                daemon=True,
            )
            t.start()
        else:
            self._run(job.id, budget, max_iterations)
        return job

    def _run(self, job_id: str, budget: int, max_iterations: int) -> None:
        job = self._jobs[job_id]
        job.status = "running"
        try:
            result = budgeted_run(
                job.goal, job.prompt,
                budget=budget, max_iterations=max_iterations, no_web=True,
            )
            job.result = result
            job.status = result.get("status", "done")
        except Exception as exc:
            job.status = "failed"
            job.error = str(exc)
            logger.exception("[JobStore] job %s failed", job_id)
        finally:
            job.finished_at = datetime.now(timezone.utc).isoformat()

    def get(self, job_id: str) -> Optional[GraphJob]:
        with self._lock:
            return self._jobs.get(job_id)

    def list(self, limit: int = 50) -> Dict[str, Any]:
        with self._lock:
            jobs = list(self._jobs.values())[-limit:]
        return {
            "count": len(jobs),
            "jobs": [
                {"id": j.id, "goal": j.goal, "status": j.status,
                 "created_at": j.created_at, "finished_at": j.finished_at}
                for j in jobs
            ],
        }

    def clear(self) -> None:
        with self._lock:
            self._jobs.clear()


# Singleton (una cola por proceso).
_job_store: Optional[GraphJobStore] = None


def get_job_store() -> GraphJobStore:
    global _job_store
    if _job_store is None:
        _job_store = GraphJobStore()
    return _job_store
