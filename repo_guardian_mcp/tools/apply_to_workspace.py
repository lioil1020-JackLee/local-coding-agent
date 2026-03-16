from __future__ import annotations

import shutil
from pathlib import Path

from repo_guardian_mcp.services.session_service import SessionService
from repo_guardian_mcp.utils.git_utils import get_git_status, run_git_command


def _get_changed_files(repo_path: Path) -> list[str]:
    status_output = get_git_status(repo_path)
    changed_files: list[str] = []

    for line in status_output.splitlines():
        if not line.strip():
            continue
        changed_files.append(line[2:].strip())

    return changed_files


def _is_workspace_file_dirty(repo_root: Path, relative_path: str) -> bool:
    output = run_git_command(repo_root, ["status", "--short", "--", relative_path])
    return bool(output.strip())


def apply_to_workspace(session_id: str) -> dict:
    session_service = SessionService("agent_runtime/sessions")
    session = session_service.load_session(session_id)

    repo_root = Path(session.repo_root).resolve()
    sandbox_root = Path(session.sandbox_path).resolve()

    changed_files = _get_changed_files(sandbox_root)

    if not changed_files:
        return {
            "ok": True,
            "session_id": session.session_id,
            "applied_files": [],
            "message": "No sandbox changes to apply.",
        }

    conflicts: list[str] = []
    applied_files: list[str] = []

    for relative_path in changed_files:
        if _is_workspace_file_dirty(repo_root, relative_path):
            conflicts.append(relative_path)
            continue

        sandbox_file = (sandbox_root / relative_path).resolve()
        workspace_file = (repo_root / relative_path).resolve()

        try:
            sandbox_file.relative_to(sandbox_root)
            workspace_file.relative_to(repo_root)
        except ValueError:
            conflicts.append(relative_path)
            continue

        if not sandbox_file.exists():
            conflicts.append(relative_path)
            continue

        workspace_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(sandbox_file, workspace_file)
        applied_files.append(relative_path)

    if conflicts:
        return {
            "ok": False,
            "session_id": session.session_id,
            "applied_files": applied_files,
            "conflicts": conflicts,
            "message": "Some files were not applied because the workspace target is dirty or invalid.",
        }

    return {
        "ok": True,
        "session_id": session.session_id,
        "applied_files": applied_files,
        "message": "Applied sandbox changes to workspace.",
    }