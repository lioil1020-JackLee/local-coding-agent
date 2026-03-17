from __future__ import annotations

"""
正式版安全修改執行器（copy‑based sandbox 版本）。

這一層的責任是將編輯流程抽象為一組可追蹤、可重試、
可停止的步驟。透過 ExecutionController 統一管理狀態、
trace、retry/stop/fallback policy，讓 orchestrator 僅負責組裝
pipeline 與對外 contract，不再內嵌錯綜複雜的控制邏輯。

步驟合約（Step Contract）
------------------------
每個 step handler 必須回傳 StepResult 物件，
包含：

- ``status``：StepStatus，表達成功、錯誤等狀態，若為 ERROR 則代表此步
  驟失敗，ExecutionController 會依 retry/stop/fallback 設定處理。
- ``output``：任意類型，表示該步驟的主要輸出；ExecutionController
  會自動將此值放入 state[step_name] 方便後續引用。
- ``summary``：人類可讀的摘要，用於 trace。缺省可為 None。
- ``updates``：字典，表示對 global state 的更新。這些鍵值對會與
  state 合併，而不必直接修改傳入的 context/state。
- ``failure_kind``：選擇性的 FailureKind，若指定將影響 retry/stop 行為。
- ``metadata``：附加資訊，將存入 trace。

任何舊的 dict 或其他型別回傳會由 ExecutionController 自動包裝成
StepResult，但推薦改為明確回傳 StepResult 以達到長期可維護性。
"""

from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

import difflib

from repo_guardian_mcp.services.execution_controller import (
    ExecutionController,
    ExecutionStep,
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
from repo_guardian_mcp.tools.create_task_session import create_task_session
from repo_guardian_mcp.tools.preview_session_diff import preview_session_diff


class EditExecutionOrchestrator:
    """
    正式版安全修改執行器（copy‑based sandbox 版本）。

    這一層的責任：
    - 用 ExecutionController 組裝正式的 step pipeline
    - 保持外部 tool contract 穩定
    - 將 retry / stop / fallback 邏輯留在 ExecutionController，
      不污染 tool 層
    """

    def __init__(self) -> None:
        # 使用獨立的 ExecutionController 實例以便追蹤與命名
        self._controller = ExecutionController()

    # ------------------------------------------------------------------
    # 外部 API
    # ------------------------------------------------------------------
    def run(
        self,
        repo_root: str,
        relative_path: str = "README.md",
        content: str = "pipeline test",
        mode: str = "append",
        old_text: Optional[str] = None,
        operations: Optional[List[dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """建立新的任務 session 並套用一次編輯。

        Parameters
        ----------
        repo_root: str
            要編輯的 repository 根目錄。
        relative_path: str
            目標檔案路徑，相對於 sandbox 根目錄。
        content: str
            欲寫入的新內容。
        mode: str
            編輯模式，支援 ``append`` ``prepend`` ``replace`` 等。
        old_text: Optional[str]
            replace 模式下欲取代的原文字串。
        operations: Optional[List[dict[str, Any]]]
            複合編輯操作，結構由 caller 定義。

        Returns
        -------
        dict
            包含 session_id、edited_files、diff、validation 等資訊。
        """
        # 初始化 context/state；不可直接修改此 dict 之外的結構
        state: Dict[str, Any] = {
            "repo_root": repo_root,
            "relative_path": relative_path,
            "content": content,
            "mode": mode,
            "old_text": old_text,
            "operations": operations,
            "session_id": None,
        }

        # 基本輸入驗證
        if not repo_root or not repo_root.strip():
            return {
                "ok": False,
                "session_id": None,
                "error": "repo_root 不能為空",
            }

        # 定義 pipeline：每一步使用 StepHandler，搭配 retry/stop 設定
        steps: List[ExecutionStep] = [
            ExecutionStep(name="create_session", handler=self._step_create_session),
            ExecutionStep(name="load_session", handler=self._step_load_session),
            ExecutionStep(name="apply_edit", handler=self._step_apply_edit),
            ExecutionStep(name="preview_diff", handler=self._step_preview_diff),
            ExecutionStep(name="validation", handler=self._step_validate),
            ExecutionStep(name="persist_session", handler=self._step_persist_session),
        ]

        result = self._controller.run(
            steps=steps,
            initial_state=state,
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
        """在既有 session 中再次執行編輯。

        Parameters
        ----------
        repo_root: str
            repository 根目錄。
        session_id: str
            已存在的 session id。
        relative_path, content, mode, old_text, operations
            同 ``run()`` 方法。
        session_result: Optional[Dict[str, Any]]
            先前 create_session 的結果，可直接帶入避免重算。

        Returns
        -------
        dict
            與 ``run()`` 相同，但不包含 create_session 的輸出。
        """
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
            ExecutionStep(name="preview_diff", handler=self._step_preview_diff),
            ExecutionStep(name="validation", handler=self._step_validate),
            ExecutionStep(name="persist_session", handler=self._step_persist_session),
        ]

        result = self._controller.run(steps=steps, initial_state=state)

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

    # ------------------------------------------------------------------
    # Step handlers
    # ------------------------------------------------------------------
    def _step_create_session(self, context: Mapping[str, Any]) -> StepResult:
        """建立新的 sandbox session。

        成功時會更新 ``session_id`` 以及 ``create_session`` 到 state，
        並將 session_id 傳回給後續步驟。
        """
        session_result = create_task_session(
            repo_root=context["repo_root"],
            create_workspace=True,
        )

        if not isinstance(session_result, dict):
            raise ValueError("create_task_session 回傳格式錯誤")

        if not session_result.get("ok", False):
            # 將工具層錯誤轉為例外，交由 ExecutionController 處理
            raise ValueError(session_result.get("error", "create_task_session 失敗"))

        session_id = session_result.get("session_id")
        if not session_id:
            raise ValueError("session_id 缺失")

        updates = {
            "session_id": session_id,
            "create_session": session_result,
        }
        summary = f"Created session {session_id}"
        return StepResult(
            status=StepStatus.SUCCESS,
            output=session_result,
            summary=summary,
            updates=updates,
        )

    def _step_load_session(self, context: Mapping[str, Any]) -> StepResult:
        """讀取既有 session metadata，驗證 sandbox 是否存在。"""
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
        summary = f"Loaded session {session.session_id}"
        return StepResult(
            status=StepStatus.SUCCESS,
            output=session_info,
            summary=summary,
            updates=updates,
        )

    def _step_apply_edit(self, context: Mapping[str, Any]) -> StepResult:
        """在 sandbox 中套用文字編輯或複合操作。"""
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

        summary = f"Applied edit to {len(edited_files)} file(s)"
        return StepResult(
            status=StepStatus.SUCCESS,
            output=edited_files,
            summary=summary,
            updates={"edited_files": edited_files},
        )

    def _step_preview_diff(self, context: Mapping[str, Any]) -> StepResult:
        """產生差異預覽，優先使用 session diff，若失敗則 fallback。"""
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

        # 選擇外部 diff 或 fallback
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
        summary = "Diff preview generated" if changed else "No changes detected"
        return StepResult(
            status=StepStatus.SUCCESS,
            output=preview,
            summary=summary,
            updates=updates,
        )

    def _step_validate(self, context: Mapping[str, Any]) -> StepResult:
        """執行 validation hook，產生摘要與狀態。"""
        session_id = context["session_id"]
        diff_text = context.get("diff_text", "") or ""
        edited_files = context.get("edited_files", [])
        changed = bool(diff_text.strip())

        # 執行外部驗證鉤子
        validation = run_validation_hook(diff_text)
        status = "validated" if validation.get("passed") else "validation_failed"

        # 若沒有實際修改，覆寫驗證結果
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

        summary_text = (
            f"Edited {len(edited_files)} file(s) in sandbox session {session_id}"
            if changed
            else f"No changes detected in sandbox session {session_id}"
        )
        updates = {
            "validation": validation,
            "status": status,
            "summary": summary_text,
        }
        return StepResult(
            status=StepStatus.SUCCESS,
            output=validation,
            summary=summary_text,
            updates=updates,
        )

    def _step_persist_session(self, context: Mapping[str, Any]) -> StepResult:
        """將更新寫回 session metadata 檔案。"""
        session_file = update_session_file(
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
        return StepResult(
            status=StepStatus.SUCCESS,
            output=session_file,
            summary="Session persisted",
            updates={"persist_session": session_file},
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _augment_semantic_diff(self, *, context: Mapping[str, Any], diff_text: str) -> str:
        """
        補上 operation‑level diff 摘要。

        原始 unified diff 在字串內替換時，常只會顯示整行變動，
        測試與上層 agent 更需要看到實際被替換的 old/new 內容。
        """
        summary_lines: List[str] = []

        operations = context.get("operations") or []
        # 當有 operation 列表時，以 replace 操作補充摘要
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
        # 單一 replace 模式補充摘要
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
        """使用 Python unified diff 產生 fallback 差異結果。"""
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
        """嘗試以多種編碼讀取檔案內容，防止編碼錯誤。"""
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

        # 若上述解碼皆失敗，最後使用 replace 模式避免拋出錯誤
        if last_error is not None:
            return data.decode("utf-8", errors="replace")
        return data.decode("utf-8", errors="replace")