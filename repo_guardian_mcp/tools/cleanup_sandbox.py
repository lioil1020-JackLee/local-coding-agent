from __future__ import annotations

from pathlib import Path

from repo_guardian_mcp.services.git_session_maintenance_service import GitSessionMaintenanceService
from repo_guardian_mcp.services.session_service import SessionService


def cleanup_sandbox(session_id: str, repo_root: str | None = None, delete_metadata: bool = True) -> dict:
    sessions_dir = Path(repo_root).resolve() / "agent_runtime" / "sessions" if repo_root else Path("agent_runtime/sessions")
    session_service = SessionService(sessions_dir)
    session = session_service.load_session(session_id)

    repo_root_path = Path(session.repo_root).resolve()
    sandbox_path = Path(session.sandbox_path).resolve()

    maintenance = GitSessionMaintenanceService(repo_root_path)
    details = maintenance.cleanup_session_artifacts(
        session_id=session_id,
        sandbox_path=sandbox_path,
        branch_name=session.branch_name,
    )

    if delete_metadata:
        session_file = sessions_dir / f"{session_id}.json"
        session_file.unlink(missing_ok=True)

    return {
        "ok": True,
        "session_id": session_id,
        "message": "Sandbox cleaned up.",
        "removed_paths": details["removed_paths"],
        "removed_branch": details["removed_branch"],
        "prune_attempted": details["prune_attempted"],
    }
