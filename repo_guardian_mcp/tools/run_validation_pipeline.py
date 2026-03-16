from __future__ import annotations

from typing import Any

from repo_guardian_mcp.services.session_update_service import update_session_file
from repo_guardian_mcp.services.validation_service import validate_session


def run_validation_pipeline(repo_root: str, session_id: str) -> dict[str, Any]:
    result = validate_session(repo_root=repo_root, session_id=session_id)

    if not result.get("ok"):
        return result

    try:
        update_session_file(
            repo_root=repo_root,
            session_id=session_id,
            updates={
                "validation": {
                    "passed": result.get("passed", False),
                    "summary": result.get("summary"),
                    "checks": result.get("checks", []),
                },
                "last_validation_status": "passed" if result.get("passed") else "failed",
                "status": "validated" if result.get("passed") else "validation_failed",
            },
        )
    except Exception as exc:
        return {
            "ok": False,
            "session_id": session_id,
            "error": f"更新 session validation 狀態失敗: {exc}",
            "validation": result,
        }

    return {
        "ok": True,
        "session_id": session_id,
        "validation": result,
        "status": "validated" if result.get("passed") else "validation_failed",
    }


# 舊空白檔的相容介面
# 讓外部若仍用 run() 也能工作。
def run(patch: dict) -> dict:
    return {"results": [], "patch": patch}
