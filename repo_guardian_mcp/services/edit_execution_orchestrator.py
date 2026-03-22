from __future__ import annotations

"""
正式版安全修改執行器（copy‑based sandbox 版本）。
"""

from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

import difflib

from repo_guardian_mcp.services.execution_controller import (
    ExecutionController,
    ExecutionStep,
    RetryPolicy,
    FallbackPolicy,
    FailureKind,
    StepResult,
    StepStatus,
)
from repo_guardian_mcp.services.sandbox_edit_service import (
    apply_text_edit,
    apply_text_operations,
)
from repo_guardian_mcp.services.session_service import SessionService
from repo_guardian_mcp.services.session_update_service import update_session_file
from repo_guardian_mcp.services.validation_hook_service import run_validation_hook
from repo_guardian_mcp.services.rollback_service import rollback_session
from repo_guardian_mcp.services.safe_edit_guard_service import SafeEditGuardService
from repo_guardian_mcp.tools.create_task_session import create_task_session
from repo_guardian_mcp.tools.preview_session_diff import preview_session_diff


class EditExecutionOrchestrator:
    def __init__(self) -> None:
        self._controller = ExecutionController()
        self._guard = SafeEditGuardService()

    def run(
        self,
        repo_root: str,
        relative_path: str = "README.md",
        content: str = "pipeline test",
        mode: str = "append",
        old_text: Optional[str] = None,
        operations: Optional[List[dict[str, Any]]] = None,
        read_only: bool = False,
    ) -> Dict[str, Any]:
        self._guard.ensure_not_read_only(read_only=read_only)
        state: Dict[str, Any] = {
            "repo_root": repo_root,
            "relative_path": relative_path,
            "content": content,
            "mode": mode,
            "old_text": old_text,
            "operations": operations,
            "session_id": None,
        }

        if not repo_root or not repo_root.strip():
            return {"ok": False, "session_id": None, "error": "repo_root 不能為空"}

        steps: List[ExecutionStep] = [
            ExecutionStep(
                name="create_session",
                handler=self._step_create_session,
                retry=RetryPolicy(
                    max_attempts=2,
                    retry_on_kinds=(FailureKind.TRANSIENT, FailureKind.TOOLING),
                    retry_on_exceptions=(),
                ),
            ),
            ExecutionStep(name="load_session", handler=self._step_load_session),
            ExecutionStep(name="apply_edit", handler=self._step_apply_edit),
            ExecutionStep(
                name="preview_diff",
                handler=self._step_preview_diff,
                retry=RetryPolicy(
                    max_attempts=2,
                    retry_on_kinds=(FailureKind.TRANSIENT, FailureKind.TOOLING),
                ),
                fallback=FallbackPolicy(
                    enabled=True,
                    fallback_step_names=("fallback_preview_diff",),
                    activate_on_kinds=(FailureKind.TRANSIENT, FailureKind.TOOLING),
                ),
            ),
            ExecutionStep(name="validation", handler=self._step_validate),
            ExecutionStep(name="persist_session", handler=self._step_persist_session),
            ExecutionStep(
                name="fallback_preview_diff",
                handler=self._step_fallback_preview_diff,
                enabled=False,
            ),
        ]

        result = self._controller.run(steps=steps, initial_state=state)

        session_id = result.context.get("session_id")
        if not result.ok:
            return {
                "ok": False,
                "session_id": session_id,
                "error": result.error,
                "execution_trace": result.trace,
            }

        validation = result.context.get("validation", {}) or {}
        if not bool(validation.get("passed", True)):
            rollback_result = rollback_session(repo_root=repo_root, session_id=session_id, cleanup_workspace=True)
            return {
                "ok": False,
                "session_id": session_id,
                "status": "rolled_back",
                "error": "validation failed; session rolled back automatically",
                "validation": validation,
                "rollback": rollback_result,
                "execution_trace": result.trace,
            }

        persist_value = result.context.get("persist_session")
        if isinstance(persist_value, Mapping):
            session_file = persist_value.get("persist_session") or persist_value.get("session_file")
        else:
            session_file = persist_value

        return {
            "ok": True,
            "session_id": session_id,
            "session": result.context.get("create_session"),
            "session_file": session_file,
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
        read_only: bool = False,
    ) -> Dict[str, Any]:
        self._guard.ensure_not_read_only(read_only=read_only)
        state: Dict[str, Any] = {
            "repo_root": repo_root,
            "session_id": session_id,
            "relative_path": relative_path,
            "content": content,
            "mode": mode,
            "old_text": old_text,
            "operations": operations,
            "create_session": session_result,
        }

        steps = [
            ExecutionStep(name="load_session", handler=self._step_load_session),
            ExecutionStep(name="apply_edit", handler=self._step_apply_edit),
            ExecutionStep(
                name="preview_diff",
                handler=self._step_preview_diff,
                retry=RetryPolicy(
                    max_attempts=2,
                    retry_on_kinds=(FailureKind.TRANSIENT, FailureKind.TOOLING),
                ),
                fallback=FallbackPolicy(
                    enabled=True,
                    fallback_step_names=("fallback_preview_diff",),
                    activate_on_kinds=(FailureKind.TRANSIENT, FailureKind.TOOLING),
                ),
            ),
            ExecutionStep(name="validation", handler=self._step_validate),
            ExecutionStep(name="persist_session", handler=self._step_persist_session),
            ExecutionStep(
                name="fallback_preview_diff",
                handler=self._step_fallback_preview_diff,
                enabled=False,
            ),
        ]

        result = self._controller.run(steps=steps, initial_state=state)

        if not result.ok:
            return {
                "ok": False,
                "session_id": session_id,
                "error": result.error,
                "execution_trace": result.trace,
            }

        validation = result.context.get("validation", {}) or {}
        if not bool(validation.get("passed", True)):
            rollback_result = rollback_session(repo_root=repo_root, session_id=session_id, cleanup_workspace=True)
            return {
                "ok": False,
                "session_id": session_id,
                "status": "rolled_back",
                "error": "validation failed; session rolled back automatically",
                "validation": validation,
                "rollback": rollback_result,
                "execution_trace": result.trace,
            }

        persist_value = result.context.get("persist_session")
        if isinstance(persist_value, Mapping):
            session_file = persist_value.get("persist_session") or persist_value.get("session_file")
        else:
            session_file = persist_value

        return {
            "ok": True,
            "session_id": session_id,
            "session": session_result,
            "session_file": session_file,
            "edited_files": result.context.get("edited_files", []),
            "diff_preview": result.context.get("preview_diff"),
            "diff_text": result.context.get("diff_text", ""),
            "changed": result.context.get("changed", False),
            "validation": result.context.get("validation", {}),
            "summary": result.context.get("summary", ""),
            "execution_trace": result.trace,
        }

    def _step_create_session(self, context: Mapping[str, Any]) -> StepResult:
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

        updates = {
            "session_id": session_id,
            "create_session": session_result,
        }
        return StepResult(
            status=StepStatus.SUCCESS,
            output=session_result,
            summary=f"Created session {session_id}",
            updates=updates,
        )

    def _step_load_session(self, context: Mapping[str, Any]) -> StepResult:
        repo_root_path = Path(context["repo_root"]).resolve()
        session_id = context.get("session_id")
        if not session_id:
            raise ValueError("session_id 不能為空")

        sessions_dir = repo_root_path / "agent_runtime" / "sessions"
        session_service = SessionService(str(sessions_dir))
        session = session_service.load_session(session_id)

        sandbox_root = Path(session.sandbox_path).resolve()
        if not sandbox_root.exists():
            raise ValueError(f"sandbox 不存在: {sandbox_root}")

        session_info: Dict[str, Any] = {
            "session_id": session.session_id,
            "repo_root": session.repo_root,
            "sandbox_path": session.sandbox_path,
            "branch_name": session.branch_name,
            "base_branch": getattr(session, "base_branch", None),
            "base_commit": session.base_commit,
            "status": session.status,
        }
        updates = {
            "sandbox_path": session.sandbox_path,
            "loaded_session": session_info,
        }
        return StepResult(
            status=StepStatus.SUCCESS,
            output=session_info,
            summary=f"Loaded session {session.session_id}",
            updates=updates,
        )

    def _step_apply_edit(self, context: Mapping[str, Any]) -> StepResult:
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

        return StepResult(
            status=StepStatus.SUCCESS,
            output=edited_files,
            summary=f"Applied edit to {len(edited_files)} file(s)",
            updates={"edited_files": edited_files},
        )

    def _step_preview_diff(self, context: Mapping[str, Any]) -> StepResult:
        session_id = context.get("session_id")
        repo_root = context.get("repo_root")
        sandbox_path = context.get("sandbox_path")
        edited_files = context.get("edited_files", [])

        diff_result: Dict[str, Any] | None = None
        if session_id:
            try:
                diff_result = preview_session_diff(session_id=session_id)
            except UnicodeDecodeError:
                diff_result = None

        if isinstance(diff_result, dict) and diff_result.get("ok", False):
            diff_text = diff_result.get("diff_text") or diff_result.get("diff", "") or ""
            diff_text = self._augment_semantic_diff(context=context, diff_text=diff_text)
            changed = bool(diff_text.strip())
            preview = dict(diff_result)
            preview["diff_text"] = diff_text
        else:
            fallback = self._build_fallback_diff(
                repo_root=repo_root,
                sandbox_path=sandbox_path,
                edited_files=edited_files,
            )
            diff_text = fallback.get("diff_text", "") or ""
            diff_text = self._augment_semantic_diff(context=context, diff_text=diff_text)
            changed = bool(diff_text.strip())
            preview = dict(fallback)
            preview["diff_text"] = diff_text

        updates = {
            "diff_text": diff_text,
            "changed": changed,
            "preview_diff": preview,
        }
        return StepResult(
            status=StepStatus.SUCCESS,
            output=preview,
            summary="Diff preview generated" if changed else "No changes detected",
            updates=updates,
        )

    def _step_validate(self, context: Mapping[str, Any]) -> StepResult:
        session_id = context["session_id"]
        diff_text = context.get("diff_text", "") or ""
        edited_files = context.get("edited_files", [])
        changed = bool(diff_text.strip())

        raw_validation = run_validation_hook(diff_text)

        if not changed:
            session_status = "no_change"
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
        else:
            validation = dict(raw_validation or {})
            passed = bool(validation.get("passed"))
            validation["status"] = "pass" if passed else "fail"
            session_status = "validated" if passed else "validation_failed"

        summary_text = (
            f"Edited {len(edited_files)} file(s) in sandbox session {session_id}"
            if changed
            else f"No changes detected in sandbox session {session_id}"
        )
        updates = {
            "validation": validation,
            "session_status": session_status,
            "summary": summary_text,
        }
        return StepResult(
            status=StepStatus.SUCCESS,
            output=validation,
            summary=summary_text,
            updates=updates,
        )

    def _step_persist_session(self, context: Mapping[str, Any]) -> StepResult:
        session_file = update_session_file(
            repo_root=context["repo_root"],
            session_id=context["session_id"],
            updates={
                "status": context.get("session_status", "pending"),
                "edited_files": context.get("edited_files", []),
                "changed": context.get("changed", False),
                "summary": context.get("summary", ""),
                "validation": context.get("validation", {}),
            },
        )
        return StepResult(
            status=StepStatus.SUCCESS,
            output=session_file,
            summary="Session persisted",
            updates={"persist_session": session_file},
        )

    def _step_fallback_preview_diff(self, context: Mapping[str, Any]) -> StepResult:
        repo_root = context.get("repo_root")
        sandbox_path = context.get("sandbox_path")
        edited_files = context.get("edited_files", [])
        try:
            fallback_result = self._build_fallback_diff(
                repo_root=repo_root,
                sandbox_path=sandbox_path,
                edited_files=edited_files,
            )
        except Exception as exc:
            return StepResult(
                status=StepStatus.ERROR,
                summary=str(exc),
                failure_kind=FailureKind.TOOLING,
            )
        diff_text = fallback_result.get("diff_text", "") or ""
        diff_text = self._augment_semantic_diff(context=context, diff_text=diff_text)
        changed = bool(diff_text.strip())
        preview = dict(fallback_result)
        preview["diff_text"] = diff_text
        updates = {
            "diff_text": diff_text,
            "changed": changed,
            "preview_diff": preview,
        }
        return StepResult(
            status=StepStatus.SUCCESS,
            output=preview,
            summary="Fallback diff generated" if changed else "No changes detected",
            updates=updates,
        )

    def _augment_semantic_diff(self, *, context: Mapping[str, Any], diff_text: str) -> str:
        summary_lines: List[str] = []

        operations = context.get("operations") or []
        if operations:
            for op in operations:
                if not isinstance(op, Mapping):
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

    def _build_fallback_diff(
        self,
        *,
        repo_root: str | None,
        sandbox_path: str | None,
        edited_files: List[str],
    ) -> Dict[str, Any]:
        if not repo_root or not sandbox_path:
            raise ValueError("無法建立 fallback diff：repo_root 或 sandbox_path 缺失")

        repo_root_path = Path(repo_root).resolve()
        sandbox_root_path = Path(sandbox_path).resolve()
        diff_chunks: List[str] = []
        changed_files: List[str] = []

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
