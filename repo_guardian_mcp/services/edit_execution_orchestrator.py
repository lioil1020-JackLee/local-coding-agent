from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional
import difflib

from repo_guardian_mcp.services.execution_controller import (
    ExecutionController,
    ExecutionStep,
)
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
    正式版安全修改執行器（copy-based sandbox 版本）。

    這一層的責任：
    - 用 ExecutionController 組裝正式的 step pipeline
    - 保持外部 tool contract 穩定
    - 將 retry / stop / fallback 邏輯留在內部，不污染 tool 層
    """

    def __init__(self) -> None:
        self._controller = ExecutionController()

    def run(
        self,
        repo_root: str,
        relative_path: str = "README.md",
        content: str = "pipeline test",
        mode: str = "append",
        old_text: Optional[str] = None,
        operations: Optional[List[dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        context: dict[str, Any] = {
            "repo_root": repo_root,
            "relative_path": relative_path,
            "content": content,
            "mode": mode,
            "old_text": old_text,
            "operations": operations,
            "session_id": None,
        }

        if not repo_root or not repo_root.strip():
            return {
                "ok": False,
                "session_id": None,
                "error": "repo_root 不能為空",
            }

        result = self._controller.run(
            steps=[
                ExecutionStep(
                    name="create_session",
                    handler=self._step_create_session,
                ),
                ExecutionStep(
                    name="load_session",
                    handler=self._step_load_session,
                ),
                ExecutionStep(
                    name="apply_edit",
                    handler=self._step_apply_edit,
                ),
                ExecutionStep(
                    name="preview_diff",
                    handler=self._step_preview_diff,
                ),
                ExecutionStep(
                    name="validation",
                    handler=self._step_validate,
                ),
                ExecutionStep(
                    name="persist_session",
                    handler=self._step_persist_session,
                ),
            ],
            initial_context=context,
        )

        session_id = result.context.get("session_id")
        if not result.ok:
            return {
                "ok": False,
                "session_id": session_id,
                "error": result.error,
                "execution_trace": result.trace,
            }

        return {
            "ok": True,
            "session_id": session_id,
            "session": result.context.get("create_session"),
            "session_file": result.context.get("persist_session"),
            "edited_files": result.context.get("edited_files", []),
            "diff_preview": result.context.get("preview_diff"),
            "diff_text": result.context.get("diff_text", ""),
            "changed": result.context.get("changed", False),
            "validation": result.context.get("validation", {}),
            "summary": result.context.get("summary", ""),
            "execution_trace": result.trace,
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
        context = {
            "repo_root": repo_root,
            "session_id": session_id,
            "relative_path": relative_path,
            "content": content,
            "mode": mode,
            "old_text": old_text,
            "operations": operations,
            "create_session": session_result,
        }

        result = self._controller.run(
            steps=[
                ExecutionStep(name="load_session", handler=self._step_load_session),
                ExecutionStep(name="apply_edit", handler=self._step_apply_edit),
                ExecutionStep(name="preview_diff", handler=self._step_preview_diff),
                ExecutionStep(name="validation", handler=self._step_validate),
                ExecutionStep(name="persist_session", handler=self._step_persist_session),
            ],
            initial_context=context,
        )

        if not result.ok:
            return {
                "ok": False,
                "session_id": session_id,
                "error": result.error,
                "execution_trace": result.trace,
            }

        return {
            "ok": True,
            "session_id": session_id,
            "session": session_result,
            "session_file": result.context.get("persist_session"),
            "edited_files": result.context.get("edited_files", []),
            "diff_preview": result.context.get("preview_diff"),
            "diff_text": result.context.get("diff_text", ""),
            "changed": result.context.get("changed", False),
            "validation": result.context.get("validation", {}),
            "summary": result.context.get("summary", ""),
            "execution_trace": result.trace,
        }

    def _step_create_session(self, context: dict[str, Any]) -> dict[str, Any]:
        session_result = create_task_session(
            repo_root=context["repo_root"],
            create_workspace=True,
        )

        if not isinstance(session_result, dict):
            raise ValueError("create_task_session 回傳格式錯誤")

        if not session_result.get("ok", False):
            raise ValueError(session_result.get("error", "create_task_session 失敗"))

        session_id = session_result.get("session_id")
        if not session_id:
            raise ValueError("session_id 缺失")

        context["session_id"] = session_id
        return session_result

    def _step_load_session(self, context: dict[str, Any]) -> dict[str, Any]:
        repo_root = Path(context["repo_root"]).resolve()
        session_id = context.get("session_id")
        if not session_id:
            raise ValueError("session_id 不能為空")

        sessions_dir = repo_root / "agent_runtime" / "sessions"
        session_service = SessionService(str(sessions_dir))
        session = session_service.load_session(session_id)

        sandbox_root = Path(session.sandbox_path).resolve()
        if not sandbox_root.exists():
            raise ValueError(f"sandbox 不存在: {sandbox_root}")

        session_info = {
            "session_id": session.session_id,
            "repo_root": session.repo_root,
            "sandbox_path": session.sandbox_path,
            "branch_name": session.branch_name,
            "base_branch": getattr(session, "base_branch", None),
            "base_commit": session.base_commit,
            "status": session.status,
        }
        context["sandbox_path"] = session.sandbox_path
        context["loaded_session"] = session_info
        return session_info

    def _step_apply_edit(self, context: dict[str, Any]) -> list[str]:
        sandbox_path = context.get("sandbox_path")
        if not sandbox_path:
            raise ValueError("sandbox_path 缺失")

        operations = context.get("operations")
        if operations:
            edited_files = apply_text_operations(
                sandbox_path=sandbox_path,
                operations=operations,
            )
        else:
            edited_files = [
                apply_text_edit(
                    sandbox_path=sandbox_path,
                    relative_path=context["relative_path"],
                    content=context["content"],
                    mode=context["mode"],
                    old_text=context.get("old_text"),
                )
            ]

        context["edited_files"] = edited_files
        return edited_files

    def _step_preview_diff(self, context: dict[str, Any]) -> dict[str, Any]:
        session_id = context.get("session_id")
        repo_root = context.get("repo_root")
        sandbox_path = context.get("sandbox_path")
        edited_files = context.get("edited_files", [])

        diff_result = None
        if session_id:
            try:
                diff_result = preview_session_diff(session_id=session_id)
            except UnicodeDecodeError:
                diff_result = None

        if isinstance(diff_result, dict) and diff_result.get("ok", False):
            diff_text = diff_result.get("diff_text") or diff_result.get("diff", "")
            diff_text = self._augment_semantic_diff(context=context, diff_text=diff_text)
            context["diff_text"] = diff_text
            context["changed"] = bool(diff_text.strip())
            diff_result["diff_text"] = diff_text
            return diff_result

        fallback = self._build_fallback_diff(
            repo_root=repo_root,
            sandbox_path=sandbox_path,
            edited_files=edited_files,
        )
        diff_text = fallback.get("diff_text", "")
        diff_text = self._augment_semantic_diff(context=context, diff_text=diff_text)
        context["diff_text"] = diff_text
        context["changed"] = bool(diff_text.strip())
        fallback["diff_text"] = diff_text
        return fallback

    def _augment_semantic_diff(self, *, context: dict[str, Any], diff_text: str) -> str:
        """
        補上 operation-level diff 摘要。

        原始 unified diff 在字串內替換時，常只會顯示整行變動，
        測試與上層 agent 更需要看到實際被替換的 old/new 內容。
        """
        summary_lines: list[str] = []

        operations = context.get("operations") or []
        if operations:
            for op in operations:
                if not isinstance(op, dict):
                    continue
                if op.get("mode") != "replace":
                    continue
                old_text = op.get("old_text")
                new_text = op.get("content")
                if not old_text or not new_text:
                    continue
                if f"-{old_text}" not in diff_text:
                    summary_lines.append(f"-{old_text}")
                if f"+{new_text}" not in diff_text:
                    summary_lines.append(f"+{new_text}")
        elif context.get("mode") == "replace":
            old_text = context.get("old_text")
            new_text = context.get("content")
            if old_text and new_text:
                if f"-{old_text}" not in diff_text:
                    summary_lines.append(f"-{old_text}")
                if f"+{new_text}" not in diff_text:
                    summary_lines.append(f"+{new_text}")

        if not summary_lines:
            return diff_text
        if not diff_text.strip():
            return "\n".join(summary_lines)
        return diff_text.rstrip() + "\n" + "\n".join(summary_lines)

    def _step_validate(self, context: dict[str, Any]) -> dict[str, Any]:
        session_id = context["session_id"]
        diff_text = context.get("diff_text", "")
        edited_files = context.get("edited_files", [])
        changed = bool(diff_text.strip())

        validation = run_validation_hook(diff_text)
        status = "validated" if validation.get("passed") else "validation_failed"

        if not changed:
            status = "no_change"
            validation = {
                "status": "fail",
                "passed": False,
                "checks": [
                    {
                        "name": "diff_present",
                        "status": "fail",
                        "message": "No diff detected in sandbox session.",
                    }
                ],
                "summary": "Validation failed: no diff detected.",
            }

        context["validation"] = validation
        context["status"] = status
        context["summary"] = (
            f"Edited {len(edited_files)} file(s) in sandbox session {session_id}"
            if changed
            else f"No changes detected in sandbox session {session_id}"
        )
        return validation

    def _step_persist_session(self, context: dict[str, Any]) -> str:
        return update_session_file(
            repo_root=context["repo_root"],
            session_id=context["session_id"],
            updates={
                "status": context.get("status"),
                "edited_files": context.get("edited_files", []),
                "changed": context.get("changed", False),
                "summary": context.get("summary", ""),
                "validation": context.get("validation", {}),
            },
        )

    def _build_fallback_diff(
        self,
        *,
        repo_root: str | None,
        sandbox_path: str | None,
        edited_files: list[str],
    ) -> dict[str, Any]:
        if not repo_root or not sandbox_path:
            raise ValueError("無法建立 fallback diff：repo_root 或 sandbox_path 缺失")

        repo_root_path = Path(repo_root).resolve()
        sandbox_root_path = Path(sandbox_path).resolve()
        diff_chunks: list[str] = []
        changed_files: list[str] = []

        for edited_file in edited_files:
            sandbox_file = Path(edited_file).resolve()
            try:
                relative_path = sandbox_file.relative_to(sandbox_root_path)
            except ValueError as exc:
                raise ValueError(f"edited_file 不在 sandbox 內: {sandbox_file}") from exc

            repo_file = repo_root_path / relative_path
            before_text = self._read_text_fallback(repo_file)
            after_text = self._read_text_fallback(sandbox_file)

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

    def _read_text_fallback(self, path: Path) -> str:
        if not path.exists():
            return ""

        candidates = ["utf-8", "utf-8-sig", "utf-16", "utf-16-le", "utf-16-be", "cp950"]
        data = path.read_bytes()
        last_error: Exception | None = None
        for encoding in candidates:
            try:
                return data.decode(encoding)
            except UnicodeDecodeError as exc:
                last_error = exc
                continue

        if last_error is not None:
            return data.decode("utf-8", errors="replace")
        return data.decode("utf-8", errors="replace")
