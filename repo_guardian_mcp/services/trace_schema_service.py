from __future__ import annotations

import time
from typing import Any


class TraceSchemaService:
    """Convert runtime traces into a stable schema for observability."""

    def build(
        self,
        *,
        task_id: str,
        session_id: str | None,
        skill: str | None,
        execution_trace: list[dict[str, Any]] | None,
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        started = time.time()
        for idx, raw in enumerate(execution_trace or [], start=1):
            rows.append(
                {
                    "task_id": task_id,
                    "session_id": session_id,
                    "skill": skill,
                    "step": str(raw.get("step_type") or raw.get("step") or raw.get("event") or f"step_{idx}"),
                    "error": raw.get("error"),
                    "latency_ms": int((time.time() - started) * 1000),
                    "checkpoint": idx,
                    "status": str(raw.get("status") or ("success" if raw.get("ok", True) else "failed")),
                    "retry_count": int(raw.get("retry_count") or 0),
                }
            )
        return rows

