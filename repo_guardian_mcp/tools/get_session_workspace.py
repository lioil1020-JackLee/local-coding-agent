from __future__ import annotations

from repo_guardian_mcp.services.session_service import SessionService


def get_session_workspace(session_id: str) -> dict:
    session_service = SessionService("agent_runtime/sessions")
    session = session_service.load_session(session_id)

    return {
        "ok": True,
        "session_id": session.session_id,
        "repo_root": session.repo_root,
        "sandbox_path": session.sandbox_path,
        "branch_name": session.branch_name,
        "base_branch": session.base_branch,
        "base_commit": session.base_commit,
        "status": session.status,
    }