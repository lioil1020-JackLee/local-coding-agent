from __future__ import annotations

"""
agent_planner 模組

這個模組負責將使用者的自然語言需求轉換為可執行的計劃。所謂的「計劃」
由多個步驟 (PlanStep) 組成，每個步驟包含要呼叫的工具類型、執行理由、
參數及重試與停止策略等。AgentPlanner 根據偵測到的意圖 (intent)
決定計劃模式 (唯讀或安全編輯) 並建立適當的步驟。

目前的實作以簡化為主，讓新手也能理解：

* 當意圖為專案分析、程式解釋或未知時，計劃為唯讀模式，步驟為
  ``analyze_repo`` 和 ``find_entrypoints``。
* 當意圖為 ``patch_apply`` 時，使用安全編輯模式。計劃包含建立
  session、套用修改、預覽差異與驗證四個步驟，並提供驗證失敗時的
  fallback 回滾策略。
* 當意圖為 ``validation_only`` 或 ``rollback`` 時，僅回覆要求提供
  ``session_id``，以免進行任何操作。
* 其他意圖則回傳唯讀模式並提示需求不明。

每個步驟預設使用 Controller 中的重試與停止邏輯，若有特殊需求可於
PlanStep 中提供自訂的 RetryPolicy 或 StopPolicy。
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional

from repo_guardian_mcp.services.execution_controller import (
    FallbackPolicy,
    RetryPolicy,
    StopPolicy,
)


# 定義允許的步驟類型字串
PlanStepType = Literal[
    "analyze_repo",
    "find_entrypoints",
    "search_code",
    "read_code_region",
    "create_task_session",
    "edit_file",
    "preview_session_diff",
    "run_validation_pipeline",
    "rollback_session",
    "respond_read_only",
]


@dataclass
class PlanStep:
    """代表計劃中的一個步驟。"""

    step_type: PlanStepType
    reason: str
    args: Dict[str, Any] = field(default_factory=dict)
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)
    stop_policy: StopPolicy = field(default_factory=StopPolicy)
    fallback_policies: List[FallbackPolicy] = field(default_factory=list)


@dataclass
class ExecutionPlan:
    """封裝 AgentPlanner 產生的完整計劃。"""

    intent: str
    mode: Literal["read_only", "safe_edit"]
    summary: str
    steps: List[PlanStep] = field(default_factory=list)


class AgentPlanner:
    """
    AgentPlanner 將使用者需求整理成可執行的計劃 (ExecutionPlan)。

    使用方式：

    ```python
    planner = AgentPlanner()
    plan = planner.build_plan(
        intent="patch_apply",
        user_request="幫我在 main.py 新增一行註解",
        repo_root="/path/to/repo",
        relative_path="main.py",
        content="# 新增註解",
        mode="append",
    )
    ```

    回傳值 ``plan`` 會包含 intent、mode、summary 和步驟列表，可供
    ConversationOrchestrator 使用。
    """

    def build_plan(
        self,
        *,
        intent: str,
        user_request: str,
        repo_root: str,
        relative_path: str = "README.md",
        content: str = "pipeline test",
        mode: str = "append_if_missing",
        old_text: Optional[str] = None,
        operations: Optional[List[dict[str, Any]]] = None,
    ) -> ExecutionPlan:
        """
        根據意圖與相關參數建立一個執行計劃。

        參數：
            intent (str): 偵測到的使用者意圖。
            user_request (str): 原始使用者請求，用於未來擴充。
            repo_root (str): 專案根目錄。
            relative_path (str): 編輯任務的相對路徑。
            content (str): 要寫入的文字。
            mode (str): 編輯模式。
            old_text (Optional[str]): 舊文字，replace 模式時使用。
            operations (Optional[List[dict]]): 複合編輯操作列表。

        回傳：
            ExecutionPlan: 構建好的計劃物件。
        """
        # 認定分析及未知意圖使用唯讀計劃
        if intent in {"project_analysis", "code_explanation", "patch_planning", "unknown"}:
            return ExecutionPlan(
                intent=intent,
                mode="read_only",
                summary="先以唯讀方式了解專案結構，避免在分析時誤改檔案。",
                steps=[
                    PlanStep(
                        step_type="analyze_repo",
                        reason="先檢視整個專案結構並建立上下文。",
                        args={"repo_root": repo_root},
                    ),
                    PlanStep(
                        step_type="find_entrypoints",
                        reason="尋找可能的入口點，方便後續理解程式流向。",
                        args={"repo_root": repo_root},
                    ),
                ],
            )

        # 安全編輯流程：先建立 session，再進行修改、預覽 diff、驗證
        if intent == "patch_apply":
            normalized_mode = self._normalize_edit_mode(mode=mode, old_text=old_text)
            edit_args: Dict[str, Any] = {
                "relative_path": relative_path,
                "content": content,
                "mode": normalized_mode,
                "old_text": old_text,
                "operations": operations,
            }

            return ExecutionPlan(
                intent=intent,
                mode="safe_edit",
                summary="建立安全修改計劃：建立 session、套用修改、預覽差異、驗證，必要時回滾。",
                steps=[
                    PlanStep(
                        step_type="create_task_session",
                        reason="建立獨立 session，確保修改在隔離環境進行。",
                        args={"repo_root": repo_root},
                        retry_policy=RetryPolicy(max_attempts=2),
                        stop_policy=StopPolicy(),
                    ),
                    PlanStep(
                        step_type="edit_file",
                        reason="根據使用者指令修改檔案，預設需滿足 idempotent。",
                        args=edit_args,
                        retry_policy=RetryPolicy(max_attempts=1),
                        stop_policy=StopPolicy(),
                    ),
                    PlanStep(
                        step_type="preview_session_diff",
                        reason="修改後先預覽差異，確認變更範圍正確。",
                        args={},
                        retry_policy=RetryPolicy(max_attempts=2),
                        stop_policy=StopPolicy(),
                    ),
                    PlanStep(
                        step_type="run_validation_pipeline",
                        reason="自動驗證修改是否符合規範，若失敗則準備回滾。",
                        args={"repo_root": repo_root},
                        retry_policy=RetryPolicy(max_attempts=1),
                        stop_policy=StopPolicy(),
                        fallback_policies=[
                            FallbackPolicy(
                                enabled=True,
                                fallback_step_names=("rollback_session",),
                            )
                        ],
                    ),
                ],
            )

        # 只做驗證但未指定 session：回覆提示
        if intent == "validation_only":
            return ExecutionPlan(
                intent=intent,
                mode="read_only",
                summary="本次需求為驗證，請提供 session_id 後再進行。",
                steps=[
                    PlanStep(
                        step_type="respond_read_only",
                        reason="缺少 session_id，無法執行驗證。",
                        args={"message": "validation_only 需要指定 session_id 才能執行驗證。"},
                    )
                ],
            )

        # 回滾但未指定 session：回覆提示
        if intent == "rollback":
            return ExecutionPlan(
                intent=intent,
                mode="read_only",
                summary="本次需求為回滾，請提供 session_id 後再進行。",
                steps=[
                    PlanStep(
                        step_type="respond_read_only",
                        reason="缺少 session_id，無法執行回滾。",
                        args={"message": "rollback 需要指定 session_id 才能執行回滾。"},
                    )
                ],
            )

        # 其他意圖：未知，保持唯讀
        return ExecutionPlan(
            intent="unknown",
            mode="read_only",
            summary="無法判斷具體需求，維持唯讀模式以保障安全。",
            steps=[
                PlanStep(
                    step_type="respond_read_only",
                    reason="需求不明確，暫不改動任何檔案。",
                    args={"message": "無法判斷需求內容，請重新描述您的目標。"},
                )
            ],
        )

    def _normalize_edit_mode(self, mode: str, old_text: str | None) -> str:
        """
        將使用者提供的 mode 正規化，並映射到實際支援的模式。

        在 copy‑based sandbox 流程中只有 ``append`` 與 ``replace`` 兩種模式。
        其中 ``append`` 具備 append_if_missing 的行為，``replace`` 具備
        replace_once 行為。此函式將各種可能輸入轉換為這兩個值。

        規則：
        - ``append`` 或 ``append_if_missing`` → ``append``
        - ``replace`` 或 ``replace_once`` → ``replace``
        - 若提供了 ``old_text``，視為 ``replace``
        - 其他未識別模式，一律回傳輸入字串，交由上層判斷
        """
        normalized = (mode or "append").strip().lower()
        if normalized in {"append", "append_if_missing"}:
            return "append"
        if normalized in {"replace", "replace_once"}:
            return "replace"
        if old_text:
            return "replace"
        return normalized