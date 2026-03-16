from __future__ import annotations

from typing import Any

from repo_guardian_mcp.services.rollback_service import rollback_session as rollback_session_service


def rollback_session(repo_root: str, session_id: str, cleanup_workspace: bool = True) -> dict[str, Any]:
    return rollback_session_service(
        repo_root=repo_root,
        session_id=session_id,
        cleanup_workspace=cleanup_workspace,
    )


# 舊相容介面保留

def run(session_id: str) -> dict[str, Any]:
    return {"rolled_back": session_id}
