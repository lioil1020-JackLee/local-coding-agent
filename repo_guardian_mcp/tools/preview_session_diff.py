from __future__ import annotations

from pathlib import Path

from repo_guardian_mcp.services.session_service import SessionService
from repo_guardian_mcp.utils.git_utils import get_diff_against_commit


def preview_session_diff(session_id: str) -> dict:
    """
    取得 sandbox worktree 與 base commit 的 diff
    """

    session_service = SessionService("agent_runtime/sessions")

    try:
        session = session_service.load_session(session_id)
    except Exception as exc:
        return {
            "ok": False,
            "error": f"load_session failed: {exc}",
            "session_id": session_id,
        }

    sandbox_path = Path(session.sandbox_path).resolve()

    if not sandbox_path.exists():
        return {
            "ok": False,
            "error": f"sandbox_path not found: {sandbox_path}",
            "session_id": session_id,
        }

    try:
        diff_text = get_diff_against_commit(sandbox_path, session.base_commit)
    except Exception as exc:
        return {
            "ok": False,
            "error": f"diff generation failed: {exc}",
            "session_id": session_id,
            "sandbox_path": str(sandbox_path),
        }

    return {
        "ok": True,
        "session_id": session.session_id,
        "sandbox_path": str(sandbox_path),
        "base_commit": session.base_commit,
        "diff": diff_text,
    }