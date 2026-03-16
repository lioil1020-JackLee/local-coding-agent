from __future__ import annotations

from typing import Any, Dict, Literal, Optional

from repo_guardian_mcp.services.edit_execution_orchestrator import EditExecutionOrchestrator

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
    正式版高階任務決策器的第一步。

    目標不是一次把所有智慧都做完，
    而是先把「理解需求」和「安全修改」責任拆開。
    """

    def __init__(
        self,
        edit_execution_orchestrator: Optional[EditExecutionOrchestrator] = None,
    ) -> None:
        self.edit_execution_orchestrator = (
            edit_execution_orchestrator or EditExecutionOrchestrator()
        )

    def detect_intent(self, user_request: str) -> Intent:
        """
        用很保守的規則先判斷意圖。
        正式版之後可再接模型或更細的 planning loop。
        """
        text = (user_request or "").strip().lower()

        if not text:
            return "unknown"

        readonly_keywords = ["分析", "看懂", "說明", "架構", "入口", "流程"]
        patch_keywords = ["修改", "幫我改", "實作", "新增", "修正", "patch"]
        rollback_keywords = ["回滾", "rollback", "還原"]
        validation_keywords = ["驗證", "測試", "檢查"]

        if any(keyword in user_request for keyword in rollback_keywords):
            return "rollback"

        if any(keyword in user_request for keyword in validation_keywords):
            return "validation_only"

        if any(keyword in user_request for keyword in patch_keywords):
            return "patch_apply"

        if any(keyword in user_request for keyword in readonly_keywords):
            return "project_analysis"

        return "unknown"

    def route(
        self,
        user_request: str,
        repo_root: str,
        relative_path: str = "README.md",
        content: str = "pipeline test",
        mode: str = "append",
        old_text: str | None = None,
        operations: list[dict[str, Any]] | None = None,
    ) -> Dict[str, Any]:
        """
        目前先做最小可用路由：
        - 分析類：只回傳判斷結果，不修改檔案
        - 修改類：交給 EditExecutionOrchestrator
        """
        intent = self.detect_intent(user_request)

        if intent in {"project_analysis", "code_explanation", "patch_planning", "unknown"}:
            return {
                "ok": True,
                "mode": "read_only",
                "intent": intent,
                "summary": "目前判定為唯讀 / 規劃任務，未進行任何檔案修改。",
            }

        if intent == "patch_apply":
            result = self.edit_execution_orchestrator.run(
                repo_root=repo_root,
                relative_path=relative_path,
                content=content,
                mode=mode,
                old_text=old_text,
                operations=operations,
            )
            result["intent"] = intent
            result["mode"] = "safe_edit"
            return result

        return {
            "ok": False,
            "intent": intent,
            "error": "此意圖尚未接上正式流程。",
        }
