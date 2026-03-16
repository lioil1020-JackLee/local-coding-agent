
from __future__ import annotations

from typing import Any, Dict, List, Optional

from repo_guardian_mcp.services.sandbox_edit_service import (
    apply_text_edit,
    apply_text_operations,
)
from repo_guardian_mcp.services.session_update_service import update_session_file
from repo_guardian_mcp.services.validation_hook_service import run_validation_hook

from repo_guardian_mcp.tools.create_task_session import create_task_session
from repo_guardian_mcp.tools.preview_session_diff import preview_session_diff


class TaskOrchestrator:
    """
    Cursor-like pipeline（Phase 1 穩定版）

    流程：
    1. 建立 sandbox task session
    2. 在 sandbox 套用文字修改
    3. 產生 diff preview
    4. 執行 validation hook
    5. 更新 session 狀態
    6. 回傳完整 pipeline 結果
    """

    def run(
        self,
        repo_root: str,
        relative_path: str = "README.md",
        content: str = "pipeline test",
        mode: str = "append",
        old_text: Optional[str] = None,
        operations: Optional[List[dict[str, Any]]] = None,
    ) -> Dict[str, Any]:

        if not repo_root or not repo_root.strip():
            raise ValueError("repo_root 不能為空")

        session_result = create_task_session(repo_root=repo_root)

        if not isinstance(session_result, dict):
            raise ValueError("create_task_session 回傳格式錯誤")

        session_id = session_result.get("session_id")
        sandbox_path = session_result.get("sandbox_path")

        if not session_id:
            raise ValueError("session_id 缺失")

        if not sandbox_path:
            raise ValueError("sandbox_path 缺失")

        if operations:
            edited_files = apply_text_operations(
                sandbox_path=sandbox_path,
                operations=operations,
            )
        else:
            edited_file = apply_text_edit(
                sandbox_path=sandbox_path,
                relative_path=relative_path,
                content=content,
                mode=mode,
                old_text=old_text,
            )
            edited_files = [edited_file]

        diff_result = preview_session_diff(session_id=session_id)

        if not isinstance(diff_result, dict):
            raise ValueError("preview_session_diff 回傳格式錯誤")

        diff_text = diff_result.get("diff", "")
        changed = bool(diff_text.strip())

        # 沒有 diff 時，不要誤判成成功修改
        if not changed:
            validation = {
                "passed": False,
                "reason": "沒有偵測到任何變更",
            }
            status = "no_change"
            summary = f"No changes detected in sandbox session {session_id}"
        else:
            validation = run_validation_hook(diff_text)
            status = "validated" if validation.get("passed") else "validation_failed"
            summary = f"Edited {len(edited_files)} file(s) in sandbox session {session_id}"

        session_file = update_session_file(
            repo_root=repo_root,
            session_id=session_id,
            updates={
                "status": status,
                "edited_files": edited_files,
                "changed": changed,
                "summary": summary,
                "validation": validation,
            },
        )

        return {
            "ok": True,
            "session_id": session_id,
            "session": session_result,
            "session_file": session_file,
            "edited_files": edited_files,
            "diff_preview": diff_result,
            "diff_text": diff_text,
            "changed": changed,
            "validation": validation,
            "summary": summary,
        }
