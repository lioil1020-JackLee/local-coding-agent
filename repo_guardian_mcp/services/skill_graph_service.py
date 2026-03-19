from __future__ import annotations


class SkillGraphService:
    def next_steps(self, intent: str) -> list[str]:
        mapping = {
            "analyze_repo": ["analyze_repo", "summarize"],
            "propose_edit": ["analyze_repo", "safe_edit"],
            "apply_edit": ["safe_edit", "validation"],
            "resume_context": ["reuse_session_context"],
        }
        return list(mapping.get(intent, []))

    def fallback_for(self, step_name: str) -> list[str]:
        mapping = {
            "safe_edit": ["inspect_failure"],
            "validation": ["rollback_or_keep_for_review"],
        }
        return list(mapping.get(step_name, []))
