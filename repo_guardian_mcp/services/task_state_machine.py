from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class TaskState(str, Enum):
    PLANNED = "planned"
    RUNNING = "running"
    VALIDATED = "validated"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass(frozen=True)
class TaskStateTransition:
    previous: TaskState | None
    current: TaskState
    event: str
    ok: bool


class TaskStateMachine:
    """Unified task state mapping for CLI/chat/session operations."""

    def transition(self, *, previous: TaskState | None, event: str, ok: bool) -> TaskStateTransition:
        normalized = (event or "").strip().lower()

        if normalized in {"plan", "preview_plan"}:
            current = TaskState.PLANNED
        elif normalized in {"rollback", "rolled_back"}:
            current = TaskState.ROLLED_BACK if ok else TaskState.FAILED
        elif normalized in {"run", "execute", "chat"}:
            current = TaskState.VALIDATED if ok else TaskState.FAILED
        elif normalized in {"session", "session_list", "session_resume", "diff", "status"}:
            current = TaskState.RUNNING if ok else TaskState.FAILED
        else:
            current = TaskState.RUNNING if ok else TaskState.FAILED

        return TaskStateTransition(previous=previous, current=current, event=event, ok=ok)

    def transition_from_payload(
        self,
        *,
        previous: TaskState | None,
        event: str,
        ok: bool,
        payload: dict[str, Any] | None = None,
    ) -> TaskStateTransition:
        if payload and payload.get("status") == "rolled_back":
            return TaskStateTransition(previous=previous, current=TaskState.ROLLED_BACK, event=event, ok=ok)
        return self.transition(previous=previous, event=event, ok=ok)

