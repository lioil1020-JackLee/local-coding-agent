from __future__ import annotations

from typing import Any, Dict, Literal, Optional

from repo_guardian_mcp.services.agent_planner import AgentPlanner, ExecutionPlan
from repo_guardian_mcp.services.edit_execution_orchestrator import EditExecutionOrchestrator
from repo_guardian_mcp.tools.analyze_repo import analyze_repo
from repo_guardian_mcp.tools.create_task_session import create_task_session
from repo_guardian_mcp.tools.find_entrypoints import find_entrypoints
from repo_guardian_mcp.tools.preview_session_diff import preview_session_diff
from repo_guardian_mcp.tools.rollback_session import rollback_session
from repo_guardian_mcp.tools.run_validation_pipeline import run_validation_pipeline

Intent = Literal[
    "project_analysis",
    "code_explanation",
    "patch_planning",
    "patch_generation",
    "patch_apply",
    "validation_only",
    "rollback",
    "unknown",
]


class ConversationOrchestrator:
    """
    正式版高階任務決策器 v2。

    第一版只做到：
    - 關鍵字判斷意圖
    - 直接路由

    第二版往前走一步：
    - 先判斷意圖
    - 再建立 plan
    - 再依 plan 執行

    這樣之後才能慢慢接近 Cursor-like agent：
    使用者說人話 → agent 自己規劃 → agent 再呼叫工具
    """

    def __init__(
        self,
        edit_execution_orchestrator: Optional[EditExecutionOrchestrator] = None,
        planner: Optional[AgentPlanner] = None,
    ) -> None:
        self.edit_execution_orchestrator = (
            edit_execution_orchestrator or EditExecutionOrchestrator()
        )
        self.planner = planner or AgentPlanner()

    def detect_intent(self, user_request: str) -> Intent:
        """
        用保守規則先判斷意圖。

        這裡故意保守，寧可先走唯讀，也不要誤改檔案。
        """
        text = (user_request or "").strip()
        lower_text = text.lower()

        if not text:
            return "unknown"

        readonly_keywords = ["分析", "看懂", "說明", "架構", "入口", "流程", "找檔案", "找入口"]
        patch_keywords = ["修改", "幫我改", "實作", "新增", "修正", "patch", "改一下", "調整"]
        rollback_keywords = ["回滾", "rollback", "還原"]
        validation_keywords = ["驗證", "測試", "檢查", "pytest", "驗一下"]

        if any(keyword in text for keyword in rollback_keywords):
            return "rollback"

        if any(keyword in text or keyword in lower_text for keyword in validation_keywords):
            return "validation_only"

        if any(keyword in text or keyword in lower_text for keyword in patch_keywords):
            return "patch_apply"

        if any(keyword in text for keyword in readonly_keywords):
            return "project_analysis"

        return "unknown"

    def build_plan(
        self,
        user_request: str,
        repo_root: str,
        relative_path: str = "README.md",
        content: str = "pipeline test",
        mode: str = "append",
        old_text: str | None = None,
        operations: list[dict[str, Any]] | None = None,
    ) -> ExecutionPlan:
        """
        對外提供明確的 build_plan 入口。

        這讓 server / 未來測試 / 未來 UI
        都可以先看 agent 打算做什麼，再決定要不要執行。
        """
        intent = self.detect_intent(user_request)
        return self.planner.build_plan(
            intent=intent,
            user_request=user_request,
            repo_root=repo_root,
            relative_path=relative_path,
            content=content,
            mode=mode,
            old_text=old_text,
            operations=operations,
        )

    def route(
        self,
        user_request: str,
        repo_root: str,
        relative_path: str = "README.md",
        content: str = "pipeline test",
        mode: str = "append",
        old_text: str | None = None,
        operations: list[dict[str, Any]] | None = None,
        session_id: str | None = None,
    ) -> Dict[str, Any]:
        """
        建立 plan 並執行。

        重要原則：
        - 分析類需求：只做唯讀工具
        - 修改類需求：一定要走 session / sandbox / validation
        """
        plan = self.build_plan(
            user_request=user_request,
            repo_root=repo_root,
            relative_path=relative_path,
            content=content,
            mode=mode,
            old_text=old_text,
            operations=operations,
        )

        if plan.mode == "read_only":
            return self._execute_read_only_plan(
                plan=plan,
                repo_root=repo_root,
                session_id=session_id,
            )

        return self._execute_safe_edit_plan(
            plan=plan,
            repo_root=repo_root,
            relative_path=relative_path,
            content=content,
            mode=mode,
            old_text=old_text,
            operations=operations,
        )

    def _execute_read_only_plan(
        self,
        *,
        plan: ExecutionPlan,
        repo_root: str,
        session_id: str | None = None,
    ) -> Dict[str, Any]:
        """
        執行唯讀計畫。
        """
        payload: Dict[str, Any] = {
            "ok": True,
            "intent": plan.intent,
            "mode": plan.mode,
            "plan_summary": plan.summary,
            "plan_steps": [
                {
                    "step_type": step.step_type,
                    "reason": step.reason,
                    "args": step.args,
                }
                for step in plan.steps
            ],
        }

        if plan.intent in {"project_analysis", "code_explanation", "patch_planning", "unknown"}:
            overview = analyze_repo(repo_root)
            entrypoints = find_entrypoints(repo_root)
            payload["analysis"] = overview
            payload["entrypoints"] = entrypoints
            payload["summary"] = "已完成唯讀分析，未修改任何檔案。"
            return payload

        if plan.intent == "validation_only":
            if not session_id:
                payload["ok"] = False
                payload["error"] = "validation_only 需要提供 session_id"
                return payload
            result = run_validation_pipeline(repo_root=repo_root, session_id=session_id)
            result["intent"] = plan.intent
            result["mode"] = "read_only"
            result["plan_summary"] = plan.summary
            result["plan_steps"] = payload["plan_steps"]
            return result

        if plan.intent == "rollback":
            if not session_id:
                payload["ok"] = False
                payload["error"] = "rollback 需要提供 session_id"
                return payload
            result = rollback_session(
                repo_root=repo_root,
                session_id=session_id,
                cleanup_workspace=True,
            )
            result["intent"] = plan.intent
            result["mode"] = "read_only"
            result["plan_summary"] = plan.summary
            result["plan_steps"] = payload["plan_steps"]
            return result

        payload["summary"] = "目前維持唯讀模式，未修改任何檔案。"
        return payload

    def _execute_safe_edit_plan(
        self,
        *,
        plan: ExecutionPlan,
        repo_root: str,
        relative_path: str,
        content: str,
        mode: str,
        old_text: str | None,
        operations: list[dict[str, Any]] | None,
    ) -> Dict[str, Any]:
        """
        執行安全修改計畫。

        第一版先保持穩定：
        直接走既有安全 edit pipeline。
        """
        result = self.edit_execution_orchestrator.run(
            repo_root=repo_root,
            relative_path=relative_path,
            content=content,
            mode=mode,
            old_text=old_text,
            operations=operations,
        )

        if not isinstance(result, dict):
            return {
                "ok": False,
                "intent": plan.intent,
                "mode": plan.mode,
                "error": "EditExecutionOrchestrator.run() 回傳格式錯誤",
                "plan_summary": plan.summary,
                "plan_steps": [
                    {
                        "step_type": step.step_type,
                        "reason": step.reason,
                        "args": step.args,
                    }
                    for step in plan.steps
                ],
            }

        result["intent"] = plan.intent
        result["mode"] = plan.mode
        result["plan_summary"] = plan.summary
        result["plan_steps"] = [
            {
                "step_type": step.step_type,
                "reason": step.reason,
                "args": step.args,
            }
            for step in plan.steps
        ]

        session_id = result.get("session_id")
        if session_id:
            diff_preview = preview_session_diff(session_id=session_id)
            result["post_edit_diff_preview"] = diff_preview

        return result
