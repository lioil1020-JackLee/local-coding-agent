from __future__ import annotations

from dataclasses import dataclass

from repo_guardian_mcp.services.agent_session_state_service import AgentSessionState


@dataclass(frozen=True)
class IntentResolution:
    intent: str
    reason: str


class IntentResolutionService:
    ANALYZE_KEYWORDS = ("分析", "analyze", "overview", "scan", "repo")
    DIFF_KEYWORDS = ("diff", "差異", "變更")
    ROLLBACK_KEYWORDS = ("rollback", "回滾", "還原", "復原")
    APPLY_KEYWORDS = ("/apply", "直接套用", "套用", "執行修改")
    STATUS_KEYWORDS = ("/status", "狀態", "進度")
    EDIT_KEYWORDS = ("修改", "新增", "重構", "patch", "edit", "change", "調整", "幫我改")

    def resolve(self, raw_text: str, state: AgentSessionState) -> IntentResolution:
        text = (raw_text or "").strip()
        lowered = text.lower()

        if not text:
            return IntentResolution("noop", "empty input")

        if text == "/status" or any(token in text for token in self.STATUS_KEYWORDS):
            return IntentResolution("show_status", "explicit status request")

        if text == "/diff" or any(token in lowered for token in self.DIFF_KEYWORDS):
            return IntentResolution("show_diff", "explicit diff request")

        if text == "/rollback" or any(token in lowered for token in self.ROLLBACK_KEYWORDS):
            return IntentResolution("rollback", "explicit rollback request")

        if text == "/apply" or any(token in lowered for token in self.APPLY_KEYWORDS):
            return IntentResolution("apply_edit", "explicit apply request")

        if any(token in lowered for token in self.ANALYZE_KEYWORDS):
            return IntentResolution("analyze_repo", "analysis keyword matched")

        if state.current_plan and state.pending_action == "apply":
            return IntentResolution("resume_context", "continue current planned task")

        if any(token in lowered for token in self.EDIT_KEYWORDS):
            return IntentResolution("propose_edit", "edit keyword matched")

        if state.last_analysis:
            return IntentResolution("resume_context", "follow-up on prior analysis")

        return IntentResolution("propose_edit", "default to planning next action")
