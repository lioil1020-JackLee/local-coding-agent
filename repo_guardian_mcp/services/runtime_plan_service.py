from __future__ import annotations

from typing import Any

from repo_guardian_mcp.skills import SkillContext


class RuntimePlanService:
    def build_context(
        self,
        *,
        repo_root: str,
        user_request: str,
        task_type: str,
        relative_path: str = "README.md",
        content: str = "",
        mode: str = "append",
        old_text: str | None = None,
        operations: list[dict[str, Any]] | None = None,
        session_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> SkillContext:
        return SkillContext(
            repo_root=repo_root,
            user_request=user_request,
            task_type=task_type,
            relative_path=relative_path,
            content=content,
            mode=mode,
            old_text=old_text,
            operations=operations,
            session_id=session_id,
            metadata=dict(metadata or {}),
        )

    def plan_outline(self, *, intent: str, selected_skill: str | None = None) -> list[str]:
        if intent == "analyze_repo":
            return ["resolve_intent", "select_skill", "execute_skill", "persist_analysis"]
        if intent in {"propose_edit", "resume_context"}:
            return ["resolve_intent", "build_edit_plan_from_context", "persist_pending_action"]
        if intent == "apply_edit":
            return ["resolve_intent", "ensure_edit_session", "execute_skill", "validate_skill", "capture_diff", "persist_state"]
        if intent == "rollback":
            return ["resolve_intent", "rollback_edit_session", "persist_state"]
        if intent == "show_diff":
            return ["resolve_intent", "load_working_diff"]
        if intent == "show_status":
            return ["resolve_intent", "render_session_status"]
        return ["resolve_intent", "select_skill"]
