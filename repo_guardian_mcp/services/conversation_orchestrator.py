from __future__ import annotations

"""
conversation_orchestrator 模組

ConversationOrchestrator 負責在高層決定如何處理使用者請求。
它根據使用者輸入偵測意圖 (intent)，透過 AgentPlanner 建立執行計劃，
並根據計劃類型 (唯讀或安全編輯) 調用對應的服務或工具。此設計讓
新手使用者可以用自然語言直接發出需求，而 Agent 會透過既定流程
處理，確保編輯行為安全並提供合理回饋。
"""

from typing import Any, Dict, List, Literal, Optional

import uuid

from repo_guardian_mcp.services.agent_planner import AgentPlanner, ExecutionPlan, PlanStep
from repo_guardian_mcp.services.edit_execution_orchestrator import EditExecutionOrchestrator
from repo_guardian_mcp.tools.analyze_repo import analyze_repo
from repo_guardian_mcp.tools.find_entrypoints import find_entrypoints
from repo_guardian_mcp.tools.rollback_session import rollback_session
from repo_guardian_mcp.tools.run_validation_pipeline import run_validation_pipeline

# 定義可能的意圖型別，便於型別檢查
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
    """高階任務決策器。偵測意圖、建立計劃並執行。"""

    def __init__(
        self,
        edit_execution_orchestrator: Optional[EditExecutionOrchestrator] = None,
        planner: Optional[AgentPlanner] = None,
    ) -> None:
        # 預先初始化子系統，以方便測試與重複使用
        self.edit_execution_orchestrator = edit_execution_orchestrator or EditExecutionOrchestrator()
        self.planner = planner or AgentPlanner()

        # conversation state: 保存每個對話的歷史訊息與計劃
        # 鍵為 conversation_id，值為列表，每個元素包含 user_request、plan、result 等
        self._conversations: Dict[str, List[Dict[str, Any]]] = {}

    # --- 意圖偵測 ---
    def detect_intent(self, user_request: str) -> Intent:
        """
        根據使用者輸入的文字判斷意圖。

        使用簡單關鍵字對照表，將需求分為幾類：分析、修改、驗證、回滾或未知。
        若判斷無法明確分類，回傳 ``unknown``。
        """
        text = (user_request or "").strip()
        lower_text = text.lower()

        if not text:
            return "unknown"  # 空指令

        readonly_keywords = ["分析", "看懂", "說明", "架構", "入口", "流程", "找檔案", "找入口"]
        patch_keywords = ["修改", "幫我改", "實作", "新增", "修正", "patch", "改一下", "調整"]
        rollback_keywords = ["回滾", "rollback", "還原"]
        validation_keywords = ["驗證", "測試", "檢查", "pytest", "驗一下"]

        # 關鍵字優先級：回滾 > 驗證 > 修改 > 分析
        if any(keyword in text or keyword in lower_text for keyword in rollback_keywords):
            return "rollback"
        if any(keyword in text or keyword in lower_text for keyword in validation_keywords):
            return "validation_only"
        if any(keyword in text or keyword in lower_text for keyword in patch_keywords):
            return "patch_apply"
        if any(keyword in text for keyword in readonly_keywords):
            return "project_analysis"
        return "unknown"

    # --- 計劃建立 ---
    def build_plan(
        self,
        user_request: str,
        repo_root: str,
        relative_path: str = "README.md",
        content: str = "pipeline test",
        mode: str = "append",
        old_text: Optional[str] = None,
        operations: List[dict[str, Any]] | None = None,
    ) -> ExecutionPlan:
        """根據使用者輸入與計劃參數建構 ExecutionPlan。"""
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

    # --- 路由與執行 ---
    def route(
        self,
        user_request: str,
        repo_root: str,
        relative_path: str = "README.md",
        content: str = "pipeline test",
        mode: str = "append",
        old_text: str | None = None,
        operations: List[dict[str, Any]] | None = None,
        session_id: str | None = None,
        conversation_id: str | None = None,
    ) -> Dict[str, Any]:
        """
        根據計劃模式執行任務。

        如果 plan.mode 為 ``read_only``，則僅執行分析或驗證/回滾等唯讀操作。
        若模式為 ``safe_edit``，則呼叫 EditExecutionOrchestrator 進行完整的
        安全編輯流程。回傳的字典會包含原始計劃的摘要與步驟描述。
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
            return self._execute_read_only_plan(plan=plan, repo_root=repo_root, session_id=session_id)

        # safe_edit 模式：呼叫 EditExecutionOrchestrator 執行修改流程
        # 需要將計劃中正規化後的模式提供給編輯工具
        resolved_mode = mode
        try:
            for step in plan.steps:
                if getattr(step, "step_type", None) == "edit_file":
                    # 計劃內的 edit_file 步驟已經包含正規化後的 mode
                    resolved_mode = step.args.get("mode", mode)
                    break
        except Exception:
            resolved_mode = mode

        if session_id:
            # 如果指定了 session_id，對既有 session 進行編輯
            result = self.edit_execution_orchestrator.edit_existing_session(
                repo_root=repo_root,
                session_id=session_id,
                relative_path=relative_path,
                content=content,
                mode=resolved_mode,
                old_text=old_text,
                operations=operations,
            )
        else:
            # 新任務：建立 session 並編輯
            result = self.edit_execution_orchestrator.run(
                repo_root=repo_root,
                relative_path=relative_path,
                content=content,
                mode=resolved_mode,
                old_text=old_text,
                operations=operations,
            )

        # 將計劃摘要併入結果
        if isinstance(result, dict):
            result.update(
                {
                    "intent": plan.intent,
                    "mode": plan.mode,
                    "plan_summary": plan.summary,
                    "plan_steps": [self._serialize_step(step) for step in plan.steps],
                }
            )
        # 紀錄對話狀態：將本次請求與計劃儲存於 conversation memory
        # 若未提供 conversation_id，為本次互動生成一個新的 id
        conv_id = conversation_id or uuid.uuid4().hex[:12]
        entry = {
            "user_request": user_request,
            "plan": plan.summary if hasattr(plan, "summary") else None,
            "intent": plan.intent if hasattr(plan, "intent") else None,
            "mode": plan.mode if hasattr(plan, "mode") else None,
            "result": result,
        }
        self._conversations.setdefault(conv_id, []).append(entry)
        # 回傳 conversation_id 以便後續多輪對話使用
        result_with_conversation = dict(result)
        result_with_conversation["conversation_id"] = conv_id
        return result_with_conversation

    # --- 唯讀計劃的執行 ---
    def _execute_read_only_plan(
        self,
        *,
        plan: ExecutionPlan,
        repo_root: str,
        session_id: str | None = None,
    ) -> Dict[str, Any]:
        """執行唯讀模式的計劃，根據 intent 執行不同工具。"""
        payload: Dict[str, Any] = {
            "ok": True,
            "intent": plan.intent,
            "mode": plan.mode,
            "plan_summary": plan.summary,
            "plan_steps": [self._serialize_step(step) for step in plan.steps],
        }

        # 分析及未知 intent：執行 repo 分析與入口點尋找
        if plan.intent in {"project_analysis", "code_explanation", "patch_planning", "unknown"}:
            payload["analysis"] = analyze_repo(repo_root)
            payload["entrypoints"] = find_entrypoints(repo_root)
            payload["summary"] = "已完成唯讀分析，未修改任何檔案。"
            return payload

        # 僅驗證 intent：需要 session_id
        if plan.intent == "validation_only":
            if not session_id:
                payload["ok"] = False
                payload["error"] = "validation_only 需要提供 session_id"
                return payload
            result = run_validation_pipeline(repo_root=repo_root, session_id=session_id)
            result.update(payload)
            return result

        # 回滾 intent：需要 session_id
        if plan.intent == "rollback":
            if not session_id:
                payload["ok"] = False
                payload["error"] = "rollback 需要提供 session_id"
                return payload
            result = rollback_session(repo_root=repo_root, session_id=session_id, cleanup_workspace=True)
            result.update(payload)
            return result

        # 其他情況：直接回傳 payload，不做任何操作
        return payload

    # --- 步驟序列化 ---
    def _serialize_step(self, step: PlanStep) -> Dict[str, Any]:
        """將 PlanStep 轉換為可序列化的字典。"""
        return {
            "step_type": step.step_type,
            "reason": step.reason,
            "args": step.args,
            "retry_policy": {
                "max_attempts": step.retry_policy.max_attempts,
                "retry_on_kinds": [kind.value for kind in step.retry_policy.retry_on_kinds],
            },
            "stop_policy": {
                "stop_on_kinds": [kind.value for kind in step.stop_policy.stop_on_kinds],
            },
            "fallback_policies": [
                {
                    "enabled": fb.enabled,
                    "fallback_step_names": list(fb.fallback_step_names),
                    "activate_on_kinds": [kind.value for kind in fb.activate_on_kinds],
                }
                for fb in step.fallback_policies
            ],
        }