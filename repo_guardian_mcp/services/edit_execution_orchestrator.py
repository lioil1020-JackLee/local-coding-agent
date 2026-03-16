from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from repo_guardian_mcp.services.sandbox_edit_service import (
    apply_text_edit,
    apply_text_operations,
)
from repo_guardian_mcp.services.session_service import SessionService
from repo_guardian_mcp.services.session_update_service import update_session_file
from repo_guardian_mcp.services.validation_hook_service import run_validation_hook
from repo_guardian_mcp.tools.create_task_session import create_task_session
from repo_guardian_mcp.tools.preview_session_diff import preview_session_diff


class EditExecutionOrchestrator:
    """
    正式版安全修改執行器的第一步。

    這一層只負責：
    1. 建立 session
    2. 在 sandbox 套用修改
    3. 產生 diff
    4. 執行 validation
    5. 寫回 session metadata
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
        session_id: Optional[str] = None

        try:
            if not repo_root or not repo_root.strip():
                return {
                    "ok": False,
                    "session_id": session_id,
                    "error": "repo_root 不能為空",
                }

            session_result = create_task_session(repo_root=repo_root)

            if not isinstance(session_result, dict):
                return {
                    "ok": False,
                    "session_id": session_id,
                    "error": "create_task_session 回傳格式錯誤",
                }

            session_id = session_result.get("session_id")

            if not session_result.get("ok", False):
                return {
                    "ok": False,
                    "session_id": session_id,
                    "error": session_result.get("error", "create_task_session 失敗"),
                    "session": session_result,
                }

            if not session_id:
                return {
                    "ok": False,
                    "session_id": session_id,
                    "error": "session_id 缺失",
                    "session": session_result,
                }

            return self.edit_existing_session(
                repo_root=repo_root,
                session_id=session_id,
                relative_path=relative_path,
                content=content,
                mode=mode,
                old_text=old_text,
                operations=operations,
                session_result=session_result,
            )

        except Exception as exc:
            return {
                "ok": False,
                "session_id": session_id,
                "error": str(exc),
            }

    def edit_existing_session(
        self,
        repo_root: str,
        session_id: str,
        relative_path: str = "README.md",
        content: str = "pipeline test",
        mode: str = "append",
        old_text: Optional[str] = None,
        operations: Optional[List[dict[str, Any]]] = None,
        session_result: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        對既有 session 的 sandbox 執行修改。
        這個方法是給新的 edit_file_tool 使用的。
        """
        if not repo_root or not repo_root.strip():
            return {
                "ok": False,
                "session_id": session_id,
                "error": "repo_root 不能為空",
            }

        if not session_id or not session_id.strip():
            return {
                "ok": False,
                "session_id": session_id,
                "error": "session_id 不能為空",
            }

        try:
            sessions_dir = Path(repo_root).resolve() / "agent_runtime" / "sessions"
            session_service = SessionService(str(sessions_dir))
            session = session_service.load_session(session_id)
        except Exception as exc:
            return {
                "ok": False,
                "session_id": session_id,
                "error": f"load_session 失敗: {exc}",
            }

        sandbox_path = session.sandbox_path

        if not sandbox_path:
            return {
                "ok": False,
                "session_id": session_id,
                "error": "sandbox_path 缺失",
            }

        try:
            edited_files = self._apply_edit(
                sandbox_path=sandbox_path,
                relative_path=relative_path,
                content=content,
                mode=mode,
                old_text=old_text,
                operations=operations,
            )
        except Exception as exc:
            return {
                "ok": False,
                "session_id": session_id,
                "error": str(exc),
            }

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
                "diff_preview": diff_result,
            }

        diff_text = diff_result.get("diff", "")
        changed = bool(diff_text.strip())

        validation, status, summary = self._build_validation_result(
            session_id=session_id,
            edited_files=edited_files,
            diff_text=diff_text,
        )

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

    def _apply_edit(
        self,
        sandbox_path: str,
        relative_path: str,
        content: str,
        mode: str,
        old_text: Optional[str],
        operations: Optional[List[dict[str, Any]]],
    ) -> List[str]:
        """根據單檔模式或多操作模式，在 sandbox 套用修改。"""
        if operations:
            return apply_text_operations(
                sandbox_path=sandbox_path,
                operations=operations,
            )

        edited_file = apply_text_edit(
            sandbox_path=sandbox_path,
            relative_path=relative_path,
            content=content,
            mode=mode,
            old_text=old_text,
        )
        return [edited_file]

    def _build_validation_result(
        self,
        session_id: str,
        edited_files: List[str],
        diff_text: str,
    ) -> tuple[Dict[str, Any], str, str]:
        """整理 diff、validation、status、summary。"""
        changed = bool(diff_text.strip())

        if not changed:
            validation = {
                "passed": False,
                "reason": "沒有偵測到任何變更",
            }
            status = "no_change"
            summary = f"No changes detected in sandbox session {session_id}"
            return validation, status, summary

        validation = run_validation_hook(diff_text)
        status = "validated" if validation.get("passed") else "validation_failed"
        summary = f"Edited {len(edited_files)} file(s) in sandbox session {session_id}"
        return validation, status, summary