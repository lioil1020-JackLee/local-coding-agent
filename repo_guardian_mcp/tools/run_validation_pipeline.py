from __future__ import annotations

"""
run_validation_pipeline 工具

此工具會重新產生指定 session 的 diff，然後呼叫驗證鉤子驗證修改內容。最後將
驗證結果和狀態寫回 session 檔案。它是 copy-based sandbox 流程中的一環，可在
編輯後獨立執行，讓使用者重新檢查改動是否符合規範。
"""

import difflib
from pathlib import Path
from typing import Dict

from repo_guardian_mcp.services.session_service import SessionService
from repo_guardian_mcp.services.session_update_service import update_session_file
from repo_guardian_mcp.services.validation_hook_service import run_validation_hook
from repo_guardian_mcp.tools.preview_session_diff import preview_session_diff


def run_validation_pipeline(
    repo_root: str,
    session_id: str,
) -> Dict[str, any]:
    """
    對指定 session 重新執行 validation。

    1. 產生 diff（使用 preview_session_diff，若失敗則 fallback）
    2. 呼叫 validation_hook 檢查 diff 是否符合規則
    3. 將驗證結果寫回 session 檔案（包含 status, validation, changed）

    參數：
        repo_root (str): 專案根目錄。
        session_id (str): 要驗證的 session ID。

    回傳：
        dict: 包含 ``ok``、``status``、``validation``、``diff_text`` 等欄位的字典。
    """
    repo_root_path = Path(repo_root).resolve()

    diff_result = None
    try:
        diff_result = preview_session_diff(session_id=session_id)
    except UnicodeDecodeError:
        diff_result = None

    if not isinstance(diff_result, dict) or not diff_result.get("ok", False):
        diff_result = _build_fallback_diff(repo_root=repo_root_path, session_id=session_id)

    diff_text = diff_result.get("diff_text") or diff_result.get("diff", "")
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


def _build_fallback_diff(*, repo_root: Path, session_id: str) -> Dict[str, any]:
    """
    當 preview_session_diff 出錯時，用此函式構建簡單的 diff。它只比較已
    編輯檔案（session.edited_files）並產生 unified diff。此路徑為最後備援，用
    於確保即便主 diff 失敗也能提供最基本的差異內容。
    """
    sessions_dir = repo_root / "agent_runtime" / "sessions"
    session_service = SessionService(str(sessions_dir))
    session = session_service.load_session(session_id)

    sandbox_root = Path(session.sandbox_path).resolve()
    edited_files = getattr(session, "edited_files", []) or []

    diff_chunks: list[str] = []
    changed_files: list[str] = []

    for edited_file in edited_files:
        sandbox_file = Path(edited_file).resolve()
        try:
            relative_path = sandbox_file.relative_to(sandbox_root)
        except ValueError as exc:
            raise ValueError(f"edited_file 不在 sandbox 內: {sandbox_file}") from exc

        repo_file = repo_root / relative_path
        before_text = _read_text_fallback(repo_file)
        after_text = _read_text_fallback(sandbox_file)

        if before_text == after_text:
            continue

        diff_chunks.append(
            "\n".join(
                difflib.unified_diff(
                    before_text.splitlines(),
                    after_text.splitlines(),
                    fromfile=str(relative_path).replace("\\", "/"),
                    tofile=str(relative_path).replace("\\", "/"),
                    lineterm="",
                )
            )
        )
        changed_files.append(str(relative_path).replace("\\", "/"))

    diff_text = "\n".join(chunk for chunk in diff_chunks if chunk).strip()
    return {
        "ok": True,
        "engine": "python_fallback",
        "changed_files": changed_files,
        "diff_text": diff_text,
    }


def _read_text_fallback(path: Path) -> str:
    """
    嘗試以多種常見編碼讀取檔案內容，避免遇到非 UTF-8 編碼檔案導致失敗。
    """
    if not path.exists():
        return ""

    data = path.read_bytes()
    for encoding in ["utf-8", "utf-8-sig", "utf-16", "utf-16-le", "utf-16-be", "cp950"]:
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue

    return data.decode("utf-8", errors="replace")