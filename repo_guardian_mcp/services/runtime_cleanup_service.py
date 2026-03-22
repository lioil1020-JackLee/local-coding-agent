from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from repo_guardian_mcp.services.session_cleanup_service import FileSessionStore, SessionCleanupService


@dataclass
class RuntimeCleanupSummary:
    sessions_reclaimed_bytes: int = 0
    agent_sessions_reclaimed_bytes: int = 0
    orphan_workspaces_reclaimed_bytes: int = 0
    sessions_deleted: int = 0
    agent_sessions_deleted: int = 0
    orphan_workspaces_deleted: int = 0

    @property
    def reclaimed_bytes(self) -> int:
        return (
            self.sessions_reclaimed_bytes
            + self.agent_sessions_reclaimed_bytes
            + self.orphan_workspaces_reclaimed_bytes
        )


class RuntimeCleanupService:
    """清理 agent_runtime 內會持續膨脹的工作資料。"""

    def _file_size(self, path: Path) -> int:
        try:
            return path.stat().st_size
        except OSError:
            return 0

    def _dir_size(self, path: Path) -> int:
        if not path.exists():
            return 0
        total = 0
        for p in path.rglob("*"):
            if p.is_file():
                total += self._file_size(p)
        return total

    def _safe_unlink(self, path: Path) -> None:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass

    def _safe_rmtree(self, path: Path) -> None:
        if not path.exists():
            return
        for child in sorted(path.rglob("*"), reverse=True):
            try:
                if child.is_file() or child.is_symlink():
                    child.unlink(missing_ok=True)
                elif child.is_dir():
                    child.rmdir()
            except OSError:
                pass
        try:
            path.rmdir()
        except OSError:
            pass

    def _cleanup_agent_sessions(
        self,
        *,
        agent_sessions_dir: Path,
        now: datetime,
        days: int,
        keep_last: int,
        dry_run: bool,
    ) -> tuple[int, int, list[str]]:
        if not agent_sessions_dir.exists():
            return 0, 0, []
        records: list[tuple[Path, datetime]] = []
        for path in sorted(agent_sessions_dir.glob("*.json")):
            try:
                mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
            except OSError:
                continue
            records.append((path, mtime))
        records.sort(key=lambda item: item[1], reverse=True)
        protected = {p for p, _ in records[: max(0, keep_last)]}
        threshold = now - timedelta(days=days)
        deleted = 0
        reclaimed = 0
        deleted_files: list[str] = []
        for path, mtime in records:
            if path in protected:
                continue
            if mtime > threshold:
                continue
            size = self._file_size(path)
            if not dry_run:
                self._safe_unlink(path)
            deleted += 1
            reclaimed += size
            deleted_files.append(path.name)
        return deleted, reclaimed, deleted_files

    def _cleanup_orphan_workspaces(
        self,
        *,
        sessions_dir: Path,
        workspaces_dir: Path,
        now: datetime,
        days: int,
        dry_run: bool,
    ) -> tuple[int, int, list[str]]:
        if not workspaces_dir.exists():
            return 0, 0, []

        live_session_ids: set[str] = {p.stem for p in sessions_dir.glob("*.json")} if sessions_dir.exists() else set()
        threshold = now - timedelta(days=days)
        deleted = 0
        reclaimed = 0
        deleted_dirs: list[str] = []

        for path in sorted(workspaces_dir.iterdir()):
            if not path.is_dir():
                continue
            if path.name in live_session_ids:
                continue
            try:
                mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
            except OSError:
                continue
            if mtime > threshold:
                continue
            size = self._dir_size(path)
            if not dry_run:
                self._safe_rmtree(path)
            deleted += 1
            reclaimed += size
            deleted_dirs.append(path.name)
        return deleted, reclaimed, deleted_dirs

    def run(
        self,
        *,
        repo_root: str,
        session_days: int = 3,
        max_sessions: int = 20,
        max_total_workspace_gb: float | None = None,
        agent_session_days: int = 14,
        keep_last_agent_sessions: int = 30,
        orphan_workspace_days: int = 3,
        dry_run: bool = False,
        aggressive: bool = False,
    ) -> dict[str, Any]:
        if aggressive:
            session_days = 0
            max_sessions = 0
            agent_session_days = 0
            keep_last_agent_sessions = 0
            orphan_workspace_days = 0

        now = datetime.now(timezone.utc)
        root = Path(repo_root).resolve()
        runtime_root = root / "agent_runtime"
        sessions_dir = runtime_root / "sessions"
        agent_sessions_dir = runtime_root / "agent_sessions"
        workspaces_dir = runtime_root / "sandbox_workspaces"
        runtime_root.mkdir(parents=True, exist_ok=True)

        summary = RuntimeCleanupSummary()
        deleted_agent_session_files: list[str] = []
        deleted_orphan_workspaces: list[str] = []

        max_total_workspace_bytes = None
        if max_total_workspace_gb is not None:
            max_total_workspace_bytes = int(max_total_workspace_gb * 1024 * 1024 * 1024)

        session_cleanup_result = None
        if sessions_dir.exists():
            if dry_run:
                session_cleanup_result = SessionCleanupService(FileSessionStore(sessions_dir)).cleanup_sessions(
                    days=session_days,
                    max_sessions=max_sessions,
                    max_total_workspace_bytes=max_total_workspace_bytes,
                    now=now,
                )
                summary.sessions_deleted = session_cleanup_result.deleted
                summary.sessions_reclaimed_bytes = session_cleanup_result.reclaimed_bytes
            else:
                session_cleanup_result = SessionCleanupService(FileSessionStore(sessions_dir)).cleanup_sessions(
                    days=session_days,
                    max_sessions=max_sessions,
                    max_total_workspace_bytes=max_total_workspace_bytes,
                    now=now,
                )
                summary.sessions_deleted = session_cleanup_result.deleted
                summary.sessions_reclaimed_bytes = session_cleanup_result.reclaimed_bytes

        deleted, reclaimed, deleted_files = self._cleanup_agent_sessions(
            agent_sessions_dir=agent_sessions_dir,
            now=now,
            days=agent_session_days,
            keep_last=keep_last_agent_sessions,
            dry_run=dry_run,
        )
        summary.agent_sessions_deleted = deleted
        summary.agent_sessions_reclaimed_bytes = reclaimed
        deleted_agent_session_files = deleted_files

        orphan_deleted, orphan_reclaimed, orphan_dirs = self._cleanup_orphan_workspaces(
            sessions_dir=sessions_dir,
            workspaces_dir=workspaces_dir,
            now=now,
            days=orphan_workspace_days,
            dry_run=dry_run,
        )
        summary.orphan_workspaces_deleted = orphan_deleted
        summary.orphan_workspaces_reclaimed_bytes = orphan_reclaimed
        deleted_orphan_workspaces = orphan_dirs

        return {
            "ok": True,
            "dry_run": dry_run,
            "aggressive": aggressive,
            "applied_policy": {
                "session_days": session_days,
                "max_sessions": max_sessions,
                "max_total_workspace_gb": max_total_workspace_gb,
                "agent_session_days": agent_session_days,
                "keep_last_agent_sessions": keep_last_agent_sessions,
                "orphan_workspace_days": orphan_workspace_days,
            },
            "repo_root": str(root),
            "runtime_root": str(runtime_root),
            "sessions_dir": str(sessions_dir),
            "agent_sessions_dir": str(agent_sessions_dir),
            "workspaces_dir": str(workspaces_dir),
            "sessions_deleted": summary.sessions_deleted,
            "agent_sessions_deleted": summary.agent_sessions_deleted,
            "orphan_workspaces_deleted": summary.orphan_workspaces_deleted,
            "reclaimed_bytes": summary.reclaimed_bytes,
            "reclaimed_mb": round(summary.reclaimed_bytes / (1024 * 1024), 2),
            "deleted_agent_session_files": deleted_agent_session_files,
            "deleted_orphan_workspaces": deleted_orphan_workspaces,
            "session_cleanup": (
                {
                    "scanned": session_cleanup_result.scanned,
                    "deleted": session_cleanup_result.deleted,
                    "reclaimed_bytes": session_cleanup_result.reclaimed_bytes,
                    "deleted_session_ids": session_cleanup_result.deleted_session_ids,
                }
                if session_cleanup_result
                else None
            ),
            "user_friendly_summary": (
                "已完成 runtime 清理，磁碟空間已回收。"
                if not dry_run
                else "已完成 dry-run，這是建議清理結果。"
            ),
            "next_actions": [
                "若結果符合預期，可移除 --dry-run 正式清理。"
                if dry_run
                else (
                    "你目前使用強力模式，建議確認重要工作區是否已備份。"
                    if aggressive
                    else "建議設定排程，每天或每週自動清理。"
                )
            ],
        }

    def build_windows_schedule_hint(
        self,
        *,
        repo_root: str,
        at_time: str = "03:30",
        task_name: str = "RepoGuardianRuntimeCleanup",
    ) -> dict[str, Any]:
        cmd = (
            f'schtasks /Create /F /SC DAILY /TN "{task_name}" /ST {at_time} '
            f'/TR "cmd /c cd /d {repo_root} && uv run repo-guardian runtime-cleanup run . --session-days 3 --max-sessions 20 --orphan-workspace-days 3"'
        )
        return {
            "ok": True,
            "task_name": task_name,
            "time": at_time,
            "schedule_command": cmd,
            "note": "請用系統管理員權限執行此指令。",
        }
