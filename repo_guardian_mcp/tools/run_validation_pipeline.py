from __future__ import annotations

from pathlib import Path

from repo_guardian_mcp.services.session_update_service import update_session_file
from repo_guardian_mcp.services.validation_hook_service import run_validation_hook
from repo_guardian_mcp.tools.preview_session_diff import preview_session_diff


def run_validation_pipeline(
    repo_root: str,
    session_id: str,
) -> dict:
    """
    對指定 session 重新執行 validation。

    copy-based sandbox 版本：
    - 直接讀 preview_session_diff
    - 對 diff_text 執行 validation hook
    - 寫回 session metadata
    """
    repo_root_path = Path(repo_root).resolve()

    diff_result = preview_session_diff(session_id=session_id)
    if not isinstance(diff_result, dict):
        return {
            "ok": False,
            "session_id": session_id,
            "error": "preview_session_diff 回傳格式錯誤",
        }

    if not diff_result.get("ok", False):
        return {
            "ok": False,
            "session_id": session_id,
            "error": diff_result.get("error", "preview_session_diff 失敗"),
        }

    diff_text = diff_result.get("diff_text") or diff_result.get("diff", "")

    if not diff_text.strip():
        validation = {
            "passed": False,
            "reason": "沒有偵測到任何變更",
        }
        status = "no_change"
    else:
        validation = run_validation_hook(diff_text)
        status = "validated" if validation.get("passed") else "validation_failed"

    session_file = update_session_file(
        repo_root=str(repo_root_path),
        session_id=session_id,
        updates={
            "status": status,
            "validation": validation,
            "changed": bool(diff_text.strip()),
        },
    )

    return {
        "ok": True,
        "session_id": session_id,
        "status": status,
        "validation": validation,
        "session_file": session_file,
        "diff_text": diff_text,
    }
