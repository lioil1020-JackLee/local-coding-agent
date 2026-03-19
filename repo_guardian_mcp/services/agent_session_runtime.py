from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from repo_guardian_mcp.services.agent_session_state_service import AgentSessionState, AgentSessionStateService
from repo_guardian_mcp.services.cli_agent_service import CLIAgentService
from repo_guardian_mcp.services.intent_resolution_service import IntentResolutionService
from repo_guardian_mcp.services.rollback_service import rollback_session
from repo_guardian_mcp.services.runtime_plan_service import RuntimePlanService
from repo_guardian_mcp.services.skill_graph_service import SkillGraphService
from repo_guardian_mcp.tools.get_session_status import get_session_status
from repo_guardian_mcp.tools.preview_session_diff import preview_session_diff


@dataclass
class RuntimeTurnResult:
    ok: bool
    mode: str
    message: str
    agent_session_id: str
    payload: dict[str, Any] = field(default_factory=dict)


class AgentSessionRuntime:
    def __init__(
        self,
        agent_service: CLIAgentService | None = None,
        intent_service: IntentResolutionService | None = None,
        runtime_plan_service: RuntimePlanService | None = None,
        skill_graph_service: SkillGraphService | None = None,
    ) -> None:
        self.agent_service = agent_service or CLIAgentService()
        self.intent_service = intent_service or IntentResolutionService()
        self.runtime_plan_service = runtime_plan_service or RuntimePlanService()
        self.skill_graph_service = skill_graph_service or SkillGraphService()

    def handle_turn(
        self,
        *,
        repo_root: str,
        raw_text: str,
        agent_session_id: str | None = None,
        default_task_type: str = "auto",
        force_plan_only: bool = False,
    ) -> RuntimeTurnResult:
        state_service = AgentSessionStateService(repo_root)
        state = state_service.get_or_create(agent_session_id, active_mode="chat")
        intent = self.intent_service.resolve(raw_text, state)
        outline = self.runtime_plan_service.plan_outline(intent=intent.intent, selected_skill=state.selected_skill)

        if intent.intent == "noop":
            return RuntimeTurnResult(True, "noop", "請輸入任務，或輸入 /help 查看指令。", state.session_id, {"intent": intent.intent, "runtime_steps": outline})

        if intent.intent == "show_status":
            payload = self._build_status_payload(state)
            return RuntimeTurnResult(True, "status", "已整理目前 agent session 狀態。", state.session_id, payload)

        if intent.intent == "show_diff":
            if not state.working_session_id:
                return RuntimeTurnResult(False, "diff", "目前沒有可預覽的 working session diff。", state.session_id, {"intent": intent.intent, "runtime_steps": outline})
            diff = preview_session_diff(state.working_session_id)
            payload = {
                "intent": intent.intent,
                "runtime_steps": outline,
                "working_session_id": state.working_session_id,
                **diff,
            }
            return RuntimeTurnResult(bool(diff.get("ok")), "diff", "已載入目前 working session 的 diff。", state.session_id, payload)

        if intent.intent == "rollback":
            if not state.working_session_id:
                return RuntimeTurnResult(False, "rollback", "目前沒有可回滾的 working session。", state.session_id, {"intent": intent.intent, "runtime_steps": outline})
            result = rollback_session(repo_root=repo_root, session_id=state.working_session_id, cleanup_workspace=True)
            if result.get("ok"):
                state.trace.append({"event": "rollback", "session_id": state.working_session_id})
                state.working_session_id = None
                state.pending_action = None
                state.last_execution = result
                state_service.save(state)
            return RuntimeTurnResult(bool(result.get("ok")), "rollback", "已回滾目前 working session。", state.session_id, {"intent": intent.intent, "runtime_steps": outline, **result})

        should_plan_only = force_plan_only or intent.intent in {"propose_edit", "resume_context"}
        task_type = self._resolve_task_type(intent=intent.intent, fallback=default_task_type)
        structured_ctx = self.runtime_plan_service.build_context(
            repo_root=repo_root,
            user_request=raw_text,
            task_type=task_type,
            session_id=state.working_session_id,
            metadata={"agent_session_id": state.session_id},
        )

        if should_plan_only:
            payload = self.agent_service.create_plan(structured_ctx)
            state.selected_skill = payload.get("selected_skill")
            state.last_user_request = raw_text
            state.current_plan = payload
            state.pending_action = "apply" if payload.get("selected_skill") == "safe_edit" else None
            state.last_structured_context = self._serialize_skill_context(structured_ctx)
            state.trace.append({"event": "plan", "intent": intent.intent, "selected_skill": payload.get("selected_skill")})
            state_service.save(state)
            payload.update({
                "intent": intent.intent,
                "runtime_steps": outline,
                "agent_session_id": state.session_id,
                "pending_action": state.pending_action,
                "skill_graph": self.skill_graph_service.next_steps(intent.intent),
            })
            return RuntimeTurnResult(True, "plan", "已建立 session-aware plan。", state.session_id, payload)

        if intent.intent == "apply_edit" and not state.last_structured_context:
            return RuntimeTurnResult(False, "run", "目前沒有可套用的既有 plan。", state.session_id, {"intent": intent.intent, "runtime_steps": outline})

        if intent.intent == "apply_edit":
            structured_ctx = self.runtime_plan_service.build_context(**state.last_structured_context, session_id=state.working_session_id)

        payload = self.agent_service.run(structured_ctx)
        state.selected_skill = payload.get("selected_skill")
        state.last_user_request = raw_text
        state.current_plan = {
            "plan_summary": payload.get("plan_summary"),
            "selected_skill": payload.get("selected_skill"),
        }
        state.last_execution = payload
        state.last_structured_context = self._serialize_skill_context(structured_ctx)
        if payload.get("selected_skill") == "analyze_repo":
            state.last_analysis = payload
            state.pending_action = None
            mode = "run"
            message = "已執行 repo 分析並寫入 session。"
        else:
            working_session_id = payload.get("session_id") or state.working_session_id
            state.working_session_id = working_session_id
            state.pending_action = None
            mode = "run"
            message = "已在既有 agent session 中執行任務。"
        state.trace.append({"event": "run", "intent": intent.intent, "selected_skill": payload.get("selected_skill")})
        state_service.save(state)
        payload.update({
            "intent": intent.intent,
            "runtime_steps": outline,
            "agent_session_id": state.session_id,
            "working_session_id": state.working_session_id,
            "skill_graph": self.skill_graph_service.next_steps(intent.intent),
        })
        return RuntimeTurnResult(bool(payload.get("ok")), mode, message, state.session_id, payload)

    def _resolve_task_type(self, *, intent: str, fallback: str) -> str:
        if intent == "analyze_repo":
            return "analyze"
        if intent in {"propose_edit", "resume_context", "apply_edit"}:
            return "edit"
        return fallback

    def _serialize_skill_context(self, ctx: Any) -> dict[str, Any]:
        return {
            "repo_root": ctx.repo_root,
            "user_request": ctx.user_request,
            "task_type": ctx.task_type,
            "relative_path": ctx.relative_path,
            "content": ctx.content,
            "mode": ctx.mode,
            "old_text": ctx.old_text,
            "operations": ctx.operations,
            "metadata": dict(ctx.metadata or {}),
        }

    def _build_status_payload(self, state: AgentSessionState) -> dict[str, Any]:
        working_session = None
        if state.working_session_id:
            working_session = get_session_status(repo_root=state.repo_root, session_id=state.working_session_id)
        return {
            "agent_session_id": state.session_id,
            "status": state.status,
            "goal": state.goal,
            "selected_skill": state.selected_skill,
            "last_user_request": state.last_user_request,
            "pending_action": state.pending_action,
            "working_session_id": state.working_session_id,
            "has_analysis": bool(state.last_analysis),
            "trace_count": len(state.trace),
            "current_plan": state.current_plan,
            "working_session": working_session,
        }
