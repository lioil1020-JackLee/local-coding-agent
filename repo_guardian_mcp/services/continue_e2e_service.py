from __future__ import annotations

from dataclasses import asdict, is_dataclass
from enum import Enum
import time
from typing import Any

from repo_guardian_mcp.tool_registry import get_tool


class ContinueE2EService:
    """模擬 Continue 端到端工具流程，驗證主線是否可用。"""

    def _json_safe(self, value: Any) -> Any:
        """將工具回傳結果轉成可 JSON 序列化格式。"""
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, Enum):
            return value.value
        if is_dataclass(value):
            return self._json_safe(asdict(value))
        if isinstance(value, dict):
            return {str(k): self._json_safe(v) for k, v in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [self._json_safe(v) for v in value]
        if hasattr(value, "__dict__"):
            return self._json_safe(vars(value))
        return str(value)

    def _call_tool(self, name: str, **kwargs: Any) -> dict[str, Any]:
        started = time.time()
        try:
            fn = get_tool(name)
            result = fn(**kwargs)
            elapsed_ms = int((time.time() - started) * 1000)
            return {
                "ok": bool(result.get("ok", True)) if isinstance(result, dict) else True,
                "tool": name,
                "elapsed_ms": elapsed_ms,
                "result": self._json_safe(result),
            }
        except Exception as exc:  # noqa: BLE001
            elapsed_ms = int((time.time() - started) * 1000)
            return {
                "ok": False,
                "tool": name,
                "elapsed_ms": elapsed_ms,
                "error": str(exc),
                "result": {},
            }

    def run(self, *, repo_root: str) -> dict[str, Any]:
        checks: list[dict[str, Any]] = []

        # 1) 規劃與分析高階流程
        checks.append(
            self._call_tool(
                "repo_guardian_preview_user_request_plan_tool",
                repo_root=repo_root,
                user_request="先幫我分析這個專案，不要改檔",
                task_type="auto",
            )
        )
        checks.append(
            self._call_tool(
                "repo_guardian_handle_user_request_tool",
                repo_root=repo_root,
                user_request="先幫我分析這個專案，不要改檔",
                task_type="auto",
                apply=False,
            )
        )

        # 2) 安全修改主線
        created = self._call_tool("repo_guardian_create_task_session_tool", repo_root=repo_root, create_workspace=True)
        checks.append(created)
        session_id = (created.get("result") or {}).get("session_id")

        if session_id:
            edited = self._call_tool(
                "repo_guardian_edit_file_tool",
                repo_root=repo_root,
                session_id=session_id,
                relative_path="README.md",
                content="continue-e2e-line",
                mode="append",
            )
            checks.append(edited)
            checks.append(
                self._call_tool(
                    "repo_guardian_preview_session_diff_tool",
                    session_id=session_id,
                )
            )
            checks.append(
                self._call_tool(
                    "repo_guardian_run_validation_pipeline_tool",
                    repo_root=repo_root,
                    session_id=session_id,
                )
            )
            checks.append(
                self._call_tool(
                    "repo_guardian_rollback_session_tool",
                    repo_root=repo_root,
                    session_id=session_id,
                    cleanup_workspace=True,
                )
            )
        else:
            checks.append(
                {
                    "ok": False,
                    "tool": "session_guard",
                    "elapsed_ms": 0,
                    "error": "create_task_session did not return session_id",
                    "result": {},
                }
            )

        passed = all(item.get("ok") for item in checks)
        total_ms = sum(int(item.get("elapsed_ms") or 0) for item in checks)
        return {
            "ok": True,
            "passed": passed,
            "repo_root": repo_root,
            "check_count": len(checks),
            "total_elapsed_ms": total_ms,
            "checks": checks,
            "user_friendly_summary": "Continue 端到端流程已驗證完成。" if passed else "Continue 端到端流程有失敗步驟。",
            "next_actions": (
                ["可直接在 Continue 進行日常操作。"]
                if passed
                else ["請先查看失敗工具與錯誤訊息，再修正後重跑。"]
            ),
        }
