from __future__ import annotations

from pathlib import Path

from repo_guardian_mcp.services.session_service import SessionService


def structured_edit(
    session_id: str,
    relative_path: str,
    new_content: str,
) -> dict:
    session_service = SessionService("agent_runtime/sessions")
    session = session_service.load_session(session_id)

    sandbox_root = Path(session.sandbox_path).resolve()
    target_path = (sandbox_root / relative_path).resolve()

    try:
        target_path.relative_to(sandbox_root)
    except ValueError:
        return {
            "ok": False,
            "error_type": "invalid_path",
            "message": "Target path escapes sandbox root.",
        }

    if not target_path.exists():
        return {
            "ok": False,
            "error_type": "file_not_found",
            "message": f"File does not exist: {relative_path}",
        }

    if not target_path.is_file():
        return {
            "ok": False,
            "error_type": "not_a_file",
            "message": f"Target is not a file: {relative_path}",
        }

    old_content = target_path.read_text(encoding="utf-8")
    target_path.write_text(new_content, encoding="utf-8")

    return {
        "ok": True,
        "session_id": session.session_id,
        "sandbox_path": session.sandbox_path,
        "relative_path": relative_path,
        "old_size": len(old_content),
        "new_size": len(new_content),
        "message": f"Updated {relative_path} in sandbox.",
    }