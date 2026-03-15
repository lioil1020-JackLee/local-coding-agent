from __future__ import annotations

from pathlib import Path

from repo_guardian_mcp.services.session_service import SessionService
from repo_guardian_mcp.utils.git_utils import get_current_branch, get_head_commit


def create_task_session(repo_root: str) -> dict:
    repo_root_path = Path(repo_root).resolve()

    session_service = SessionService("agent_runtime/sessions")
    session_id = session_service.new_session_id()

    sandbox_path = Path("agent_runtime/sandbox_worktrees") / session_id
    branch_name = f"rg/session-{session_id}"
    base_branch = get_current_branch(repo_root_path)
    base_commit = get_head_commit(repo_root_path)

    session = session_service.build_session(
        session_id=session_id,
        repo_root=repo_root_path,
        sandbox_path=sandbox_path,
        branch_name=branch_name,
        base_branch=base_branch,
        base_commit=base_commit,
    )

    session_service.save_session(session)

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