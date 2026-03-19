from __future__ import annotations

from dataclasses import asdict
from typing import Any

from repo_guardian_mcp.services.execution_controller import ExecutionController, ExecutionPlan, ExecutionStep, StepResult
from repo_guardian_mcp.skills import AnalyzeRepoSkill, SafeEditSkill, SkillContext, SkillPlan, SkillRegistry, SkillResult


class CLIAgentService:
    def __init__(self, skill_registry: SkillRegistry | None = None, controller: ExecutionController | None = None) -> None:
        self.skill_registry = skill_registry or SkillRegistry([AnalyzeRepoSkill(), SafeEditSkill()])
        self.controller = controller or ExecutionController(handlers={"preview_plan": self._step_preview_plan, "select_skill": self._step_select_skill, "execute_skill": self._step_execute_skill, "validate_skill": self._step_validate_skill, "finalize": self._step_finalize})

    def build_context(self, *, repo_root: str, user_request: str = "", task_type: str = "auto", relative_path: str = "README.md", content: str = "", mode: str = "append", old_text: str | None = None, operations: list[dict[str, Any]] | None = None, session_id: str | None = None, metadata: dict[str, Any] | None = None) -> SkillContext:
        return SkillContext(repo_root=repo_root, user_request=user_request, task_type=task_type, relative_path=relative_path, content=content, mode=mode, old_text=old_text, operations=operations, session_id=session_id, metadata=dict(metadata or {}))

    def create_plan(self, ctx: SkillContext) -> dict[str, Any]:
        skill = self.skill_registry.choose(ctx)
        skill_plan = skill.plan(ctx)
        execution_plan = self._build_execution_plan(skill_plan)
        return {"ok": True, "selected_skill": skill.name, "skill_description": getattr(skill, "description", ""), "plan_summary": skill_plan.summary, "skill_plan": asdict(skill_plan), "execution_steps": [step.action for step in execution_plan.steps]}

    def run(self, ctx: SkillContext) -> dict[str, Any]:
        preview = self.create_plan(ctx)
        execution_plan = self._build_execution_plan(SkillPlan(**preview["skill_plan"]))
        outcome = self.controller.run(execution_plan, initial_state={"skill_context": ctx, "plan_preview": preview})
        state = outcome.context.state
        validation = dict(state.get("skill_validation") or {})
        skill_result = state.get("skill_result") or {}
        response = {"ok": outcome.ok, "status": outcome.context.status.value, "selected_skill": preview["selected_skill"], "plan_summary": preview["plan_summary"], "skill_validation": validation, "execution_trace": [{"step_id": item.step_id, "step_type": item.step_type, "status": item.status.value, "error": item.error, "retry_count": item.retry_count} for item in outcome.trace]}
        if isinstance(skill_result, dict):
            response.update(skill_result)
        if not outcome.ok:
            response.setdefault("error", outcome.error)
        return response

    def _build_execution_plan(self, skill_plan: SkillPlan) -> ExecutionPlan:
        return ExecutionPlan(plan_id=f"plan:{skill_plan.skill_name}", summary=skill_plan.summary, task_type=skill_plan.intent, requires_validation=skill_plan.requires_validation, requires_session=skill_plan.requires_session, steps=[ExecutionStep(name="preview_plan", action="preview_plan"), ExecutionStep(name="select_skill", action="select_skill"), ExecutionStep(name="execute_skill", action="execute_skill"), ExecutionStep(name="validate_skill", action="validate_skill"), ExecutionStep(name="finalize", action="finalize")])

    def _step_preview_plan(self, step, ctx) -> StepResult:
        return StepResult.success(**dict(ctx.state.get("plan_preview") or {}))

    def _step_select_skill(self, step, ctx) -> StepResult:
        skill_ctx = ctx.state["skill_context"]
        skill = self.skill_registry.choose(skill_ctx)
        skill_plan = skill.plan(skill_ctx)
        return StepResult(output={"selected_skill": skill.name, "skill_description": getattr(skill, "description", ""), "skill_plan": asdict(skill_plan)}, updates={"selected_skill": skill.name, "skill_instance": skill, "skill_plan": asdict(skill_plan)})

    def _step_execute_skill(self, step, ctx) -> StepResult:
        skill_ctx = ctx.state["skill_context"]
        skill = ctx.state["skill_instance"]
        skill_plan = SkillPlan(**ctx.state["skill_plan"])
        result = skill.execute(skill_ctx, skill_plan)
        if result.error:
            return StepResult.failed(result.error, result=result.output)
        return StepResult(output={"ok": result.ok, "skill_result": result.output, "session_id": result.session_id}, updates={"skill_result": result.output, "session_id": result.session_id})

    def _step_validate_skill(self, step, ctx) -> StepResult:
        skill_ctx = ctx.state["skill_context"]
        skill = ctx.state["skill_instance"]
        raw = dict(ctx.state.get("skill_result") or {})
        skill_result = SkillResult(ok=bool(raw.get("ok", True)), skill_name=ctx.state.get("selected_skill", ""), output=raw, error=raw.get("error"), validation=dict(raw.get("validation") or {}), session_id=raw.get("session_id"))
        validation = skill.validate(skill_ctx, skill_result)
        if not validation.get("passed"):
            return StepResult.failed(validation.get("summary") or "skill validation failed", validation=validation)
        return StepResult(output={"skill_validation": validation}, updates={"skill_validation": validation})

    def _step_finalize(self, step, ctx) -> StepResult:
        return StepResult.success(summary=ctx.state.get("plan_preview", {}).get("plan_summary", ""), selected_skill=ctx.state.get("selected_skill"))
