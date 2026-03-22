from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from repo_guardian_mcp.services.rollback_service import rollback_session
from repo_guardian_mcp.services.task_state_machine import TaskStateMachine
from repo_guardian_mcp.tools.list_sessions import list_sessions_tool
from repo_guardian_mcp.tools.preview_session_diff import preview_session_diff
from repo_guardian_mcp.tools.resume_session import resume_session_tool


class SessionLifecycleContractService:
    """Unified contract for session list/resume/diff/rollback lifecycle operations."""

    def __init__(self, state_machine: TaskStateMachine | None = None) -> None:
        self.state_machine = state_machine or TaskStateMachine()

    def _sessions_dir(self, repo_root: str) -> str:
        return str((Path(repo_root).resolve() / "agent_runtime" / "sessions").resolve())

    def list(self, *, repo_root: str, include_cleaned: bool = False) -> dict[str, Any]:
        result = list_sessions_tool(self._sessions_dir(repo_root), include_cleaned=include_cleaned)
        ok = bool(result.get("ok"))
        transition = self.state_machine.transition(previous=None, event="session_list", ok=ok)
        return {
            "ok": ok,
            "operation": "session_list",
            "task_state": transition.current.value,
            "status_code": "ok" if ok else "session_list_failed",
            **result,
        }

    def resume(self, *, repo_root: str, session_id: str) -> dict[str, Any]:
        result = resume_session_tool(self._sessions_dir(repo_root), session_id=session_id)
        ok = bool(result.get("ok"))
        transition = self.state_machine.transition(previous=None, event="session_resume", ok=ok)
        return {
            "ok": ok,
            "operation": "session_resume",
            "task_state": transition.current.value,
            "status_code": "ok" if ok else "session_resume_failed",
            **result,
        }

    def diff(self, *, repo_root: str, session_id: str) -> dict[str, Any]:
        previous = Path.cwd()
        try:
            os.chdir(repo_root)
            result = preview_session_diff(session_id)
        finally:
            os.chdir(str(previous))

        ok = bool(result.get("ok"))
        transition = self.state_machine.transition(previous=None, event="diff", ok=ok)
        payload = dict(result)
        if ok:
            payload["changed_file_count"] = len(payload.get("changed_files") or [])
        return {
            "ok": ok,
            "operation": "diff",
            "task_state": transition.current.value,
            "status_code": "ok" if ok else "diff_failed",
            **payload,
        }

    def rollback(self, *, repo_root: str, session_id: str, keep_workspace: bool = False) -> dict[str, Any]:
        result = rollback_session(repo_root=repo_root, session_id=session_id, cleanup_workspace=not keep_workspace)
        ok = bool(result.get("ok"))
        transition = self.state_machine.transition_from_payload(previous=None, event="rollback", ok=ok, payload=result)
        return {
            "ok": ok,
            "operation": "rollback",
            "task_state": transition.current.value,
            "status_code": "ok" if ok else "rollback_failed",
            **result,
        }
