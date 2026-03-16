from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from repo_guardian_mcp.services.session_service import SessionService
from repo_guardian_mcp.services.session_update_service import update_session_file
from repo_guardian_mcp.utils.git_utils import run_git_command


# 舊相容介面保留。
def rollback(session_id: str) -> dict[str, Any]:
    return {"rolled_back": session_id}


class RollbackService:
    """將 session 標記為回滾，並清掉 sandbox worktree。"""

    def __init__(self, repo_root: str | Path) -> None:
        self.repo_root = Path(repo_root).resolve()
        self.sessions_root = self.repo_root / "agent_runtime" / "sessions"
        self.session_service = SessionService(self.sessions_root)

    def rollback_session(self, session_id: str, cleanup_workspace: bool = True) -> dict[str, Any]:
        if not session_id or not session_id.strip():
            return {
                "ok": False,
                "error": "session_id 不能為空",
            }

        try:
            session = self.session_service.load_session(session_id)
        except Exception as exc:
            return {
                "ok": False,
                "error": f"load_session 失敗: {exc}",
                "session_id": session_id,
            }

        sandbox_path = Path(session.sandbox_path).resolve()
        branch_name = session.branch_name
        cleanup_actions: list[str] = []
        warnings: list[str] = []

        if cleanup_workspace and sandbox_path.exists():
            try:
                run_git_command(self.repo_root, ["worktree", "remove", "--force", str(sandbox_path)])
                cleanup_actions.append(f"removed worktree: {sandbox_path}")
            except Exception as exc:
                warnings.append(f"git worktree remove 失敗，改用資料夾刪除: {exc}")
                try:
                    shutil.rmtree(sandbox_path, ignore_errors=True)
                    cleanup_actions.append(f"deleted sandbox dir: {sandbox_path}")
                except Exception as rm_exc:
                    warnings.append(f"刪除 sandbox 失敗: {rm_exc}")

        if branch_name:
            try:
                run_git_command(self.repo_root, ["branch", "-D", branch_name])
                cleanup_actions.append(f"deleted branch: {branch_name}")
            except Exception as exc:
                warnings.append(f"刪除 branch 失敗: {exc}")

        try:
            session_file = update_session_file(
                repo_root=str(self.repo_root),
                session_id=session_id,
                updates={
                    "status": "rolled_back",
                    "changed": False,
                    "summary": "session 已回滾並清理 sandbox",
                },
            )
        except Exception as exc:
            return {
                "ok": False,
                "session_id": session_id,
                "error": f"更新 session 狀態失敗: {exc}",
                "warnings": warnings,
                "cleanup_actions": cleanup_actions,
            }

        return {
            "ok": True,
            "session_id": session_id,
            "status": "rolled_back",
            "session_file": session_file,
            "cleanup_actions": cleanup_actions,
            "warnings": warnings,
        }


def rollback_session(repo_root: str, session_id: str, cleanup_workspace: bool = True) -> dict[str, Any]:
    return RollbackService(repo_root).rollback_session(
        session_id=session_id,
        cleanup_workspace=cleanup_workspace,
    )
