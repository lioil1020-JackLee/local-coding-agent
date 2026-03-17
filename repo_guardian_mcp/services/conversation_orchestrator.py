from __future__ import annotations

from typing import Any, Dict, Literal, Optional

from repo_guardian_mcp.services.agent_planner import AgentPlanner, ExecutionPlan
from repo_guardian_mcp.services.edit_execution_orchestrator import EditExecutionOrchestrator
from repo_guardian_mcp.tools.analyze_repo import analyze_repo
from repo_guardian_mcp.tools.find_entrypoints import find_entrypoints
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
    """正式版高階任務決策器。"""

    def __init__(
        self,
        edit_execution_orchestrator: Optional[EditExecutionOrchestrator] = None,
        planner: Optional[AgentPlanner] = None,
    ) -> None:
        self.edit_execution_orchestrator = edit_execution_orchestrator or EditExecutionOrchestrator()
        self.planner = planner or AgentPlanner()

    def detect_intent(self, user_request: str) -> Intent:
        text = (user_request or "").strip()
        lower_text = text.lower()

        if not text:
            return "unknown"

        readonly_keywords = ["分析", "看懂", "說明", "架構", "入口", "流程", "找檔案", "找入口"]
        patch_keywords = ["修改", "幫我改", "實作", "新增", "修正", "patch", "改一下", "調整"]
        rollback_keywords = ["回滾", "rollback", "還原"]
        validation_keywords = ["驗證", "測試", "檢查", "pytest", "驗一下"]

        if any(keyword in text or keyword in lower_text for keyword in rollback_keywords):
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
        mode: str = "append_if_missing",
        old_text: str | None = None,
        operations: list[dict[str, Any]] | None = None,
    ) -> ExecutionPlan:
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
        mode: str = "append_if_missing",
        old_text: str | None = None,
        operations: list[dict[str, Any]] | None = None,
        session_id: str | None = None,
    ) -> Dict[str, Any]:
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
            return self._execute_read_only_plan(plan=plan, repo_root=repo_root, session_id=session_id)

        result = self.edit_execution_orchestrator.run(
            repo_root=repo_root,
            relative_path=relative_path,
            content=content,
            mode=mode,
            old_text=old_text,
            operations=operations,
        )
        result["intent"] = plan.intent
        result["mode"] = plan.mode
        result["plan_summary"] = plan.summary
        result["plan_steps"] = [self._serialize_step(step) for step in plan.steps]
        return result

    def _execute_read_only_plan(
        self,
        *,
        plan: ExecutionPlan,
        repo_root: str,
        session_id: str | None = None,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "ok": True,
            "intent": plan.intent,
            "mode": plan.mode,
            "plan_summary": plan.summary,
            "plan_steps": [self._serialize_step(step) for step in plan.steps],
        }

        if plan.intent in {"project_analysis", "code_explanation", "patch_planning", "unknown"}:
            payload["analysis"] = analyze_repo(repo_root)
            payload["entrypoints"] = find_entrypoints(repo_root)
            payload["summary"] = "已完成唯讀分析，未修改任何檔案。"
            return payload

        if plan.intent == "validation_only":
            if not session_id:
                payload["ok"] = False
                payload["error"] = "validation_only 需要提供 session_id"
                return payload
            result = run_validation_pipeline(repo_root=repo_root, session_id=session_id)
            result.update(payload)
            return result

        if plan.intent == "rollback":
            if not session_id:
                payload["ok"] = False
                payload["error"] = "rollback 需要提供 session_id"
                return payload
            result = rollback_session(repo_root=repo_root, session_id=session_id, cleanup_workspace=True)
            result.update(payload)
            return result

        return payload

    def _serialize_step(self, step: Any) -> Dict[str, Any]:
        return {
            "step_type": step.step_type,
            "reason": step.reason,
            "args": step.args,
            "retry_policy": {
                "max_attempts": step.retry_policy.max_attempts,
                "retry_on_error_codes": list(step.retry_policy.retry_on_error_codes),
            },
            "stop_policy": {
                "stop_on_failure": step.stop_policy.stop_on_failure,
                "stop_on_no_change": step.stop_policy.stop_on_no_change,
                "stop_error_codes": list(step.stop_policy.stop_error_codes),
            },
            "fallback_policies": [
                {
                    "step_type": fallback.step_type,
                    "args": fallback.args,
                    "reason": fallback.reason,
                }
                for fallback in step.fallback_policies
            ],
        }
