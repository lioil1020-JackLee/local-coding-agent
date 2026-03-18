from __future__ import annotations

from pathlib import Path
from random import random

from repo_guardian_mcp.services.git_session_maintenance_service import GitSessionMaintenanceService
from repo_guardian_mcp.services.session_cleanup_service import FileSessionStore, SessionCleanupService


class SessionLifecycleCoordinator:
    """統一 session lifecycle 操作。

    這個協調器同時支援兩種初始化方式：
    1. 傳入 repo root，例如 ``E:/py/local-coding-agent``
    2. 傳入 sessions 目錄，例如 ``.../agent_runtime/sessions``

    這樣可保持與既有 tools/tests 的相容性。
    """

    def __init__(self, repo_root_or_sessions_dir: str | Path) -> None:
        input_path = Path(repo_root_or_sessions_dir).resolve()

        if input_path.name == "sessions":
            self.sessions_dir = input_path
            self.repo_root = input_path.parent.parent
        else:
            self.repo_root = input_path
            self.sessions_dir = self.repo_root / "agent_runtime" / "sessions"

        self.session_store = FileSessionStore(self.sessions_dir)
        self.cleanup = SessionCleanupService(self.session_store)
        self.git_maintenance = GitSessionMaintenanceService(self.repo_root)

    def touch_session(self, session_id: str, ttl_days: int = 3):
        return self.cleanup.touch_session(session_id=session_id, ttl_days=ttl_days)

    def pin_session(self, session_id: str, pinned: bool = True):
        return self.cleanup.pin_session(session_id=session_id, pinned=pinned)

    def cleanup_sessions(
        self,
        days: int = 3,
        max_sessions: int = 20,
        max_total_workspace_bytes: int | None = None,
    ):
        result = self.cleanup.cleanup_sessions(
            days=days,
            max_sessions=max_sessions,
            max_total_workspace_bytes=max_total_workspace_bytes,
        )
        self.git_maintenance.prune_worktrees()
        return result

    def list_sessions(self):
        return self.session_store.list_sessions()

    def resume_session(self, session_id: str, ttl_days: int = 3):
        return self.touch_session(session_id=session_id, ttl_days=ttl_days)

    def maybe_cleanup(
        self,
        *,
        probability: float = 0.1,
        days: int = 3,
        max_sessions: int = 20,
        max_total_workspace_bytes: int | None = None,
    ):
        if probability <= 0:
            return None
        if probability < 1.0 and random() >= probability:
            return None
        return self.cleanup_sessions(
            days=days,
            max_sessions=max_sessions,
            max_total_workspace_bytes=max_total_workspace_bytes,
        )
