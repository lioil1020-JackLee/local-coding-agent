from __future__ import annotations

import time
import uuid
from typing import Any

from repo_guardian_mcp.services.error_diagnosis_service import ErrorDiagnosisService
from repo_guardian_mcp.services.task_state_machine import TaskState, TaskStateMachine
from repo_guardian_mcp.services.trace_schema_service import TraceSchemaService
from repo_guardian_mcp.services.trace_summary_service import TraceSummaryService
from repo_guardian_mcp.services.user_friendly_summary_service import UserFriendlySummaryService


class ResponseEnvelopeService:
    """Build a stable response envelope for CLI/chat/bridge surfaces."""

    def __init__(
        self,
        state_machine: TaskStateMachine | None = None,
        diagnosis_service: ErrorDiagnosisService | None = None,
    ) -> None:
        self.state_machine = state_machine or TaskStateMachine()
        self.diagnosis_service = diagnosis_service or ErrorDiagnosisService()
        self.trace_summary_service = TraceSummaryService()
        self.trace_schema_service = TraceSchemaService()
        self.user_summary_service = UserFriendlySummaryService()

    def new_trace_ref(self, scope: str = "task") -> str:
        return f"{scope}-{int(time.time() * 1000)}-{uuid.uuid4().hex[:8]}"

    def wrap(
        self,
        *,
        mode: str,
        message: str,
        ok: bool,
        data: dict[str, Any] | None = None,
        error: str | None = None,
        trace_ref: str | None = None,
        previous_state: TaskState | None = None,
    ) -> dict[str, Any]:
        data = dict(data or {})
        trace_ref = trace_ref or self.new_trace_ref(mode or "task")
        transition = self.state_machine.transition_from_payload(
            previous=previous_state,
            event=mode,
            ok=ok,
            payload=data,
        )
        error_block = self.diagnosis_service.build_error_block(error=error, payload=data)
        task_id = str(data.get("task_id") or trace_ref)
        if "standardized_trace" not in data:
            minimal_trace = [{"step_type": mode, "status": "success" if ok else "failed", "error": error}]
            data["standardized_trace"] = self.trace_schema_service.build(
                task_id=task_id,
                session_id=data.get("session_id"),
                skill=data.get("selected_skill"),
                execution_trace=minimal_trace,
            )
        if "trace_summary" not in data:
            trace_summary = self.trace_summary_service.summarize(
                [
                    {
                        "step_id": "1",
                        "step_type": mode,
                        "status": "success" if ok else "failed",
                        "error": error,
                        "retry_count": 0,
                    }
                ]
            )
            data["trace_summary"] = trace_summary
            data["trace_summary_text"] = trace_summary["text"]

        user_summary = self.user_summary_service.build(
            mode=mode,
            ok=ok,
            message=message,
            task_state=transition.current.value,
            data=data,
            error_code=(error_block.get("code") if error_block else None),
        )
        data.setdefault("user_friendly_summary", user_summary["user_friendly_summary"])
        data.setdefault("next_actions", user_summary["next_actions"])

        envelope = {
            "ok": ok,
            "mode": mode,
            "message": message,
            "data": data,
            "error": error_block,
            "error_code": error_block.get("code") if error_block else None,
            "trace_ref": trace_ref,
            "task_state": transition.current.value,
            "user_friendly_summary": data.get("user_friendly_summary"),
            "next_actions": data.get("next_actions"),
        }

        # Backward-compatible flattening for existing callers/tests.
        for key, value in data.items():
            envelope.setdefault(key, value)
        if error and envelope["error"] is None:
            envelope["error"] = {"code": "execution_error", "message": error}
        return envelope
