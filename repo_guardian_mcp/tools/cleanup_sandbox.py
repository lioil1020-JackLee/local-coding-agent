from __future__ import annotations

from pathlib import Path

from repo_guardian_mcp.services.session_service import SessionService
from repo_guardian_mcp.utils.git_utils import run_git_command


def cleanup_sandbox(session_id: str) -> dict:
    session_service = SessionService("agent_runtime/sessions")
    session = session_service.load_session(session_id)

    repo_root = Path(session.repo_root).resolve()
    sandbox_path = Path(session.sandbox_path).resolve()

    try:
        run_git_command(repo_root, ["worktree", "remove", "--force", str(sandbox_path)])
    except Exception as exc:
        return {
            "ok": False,
            "message": f"Failed to remove worktree: {exc}",
        }

    try:
        session_file = Path("agent_runtime/sessions") / f"{session_id}.json"
        if session_file.exists():
            session_file.unlink()
    except Exception:
        pass

    return {
        "ok": True,
        "session_id": session_id,
        "message": "Sandbox cleaned up.",
    }