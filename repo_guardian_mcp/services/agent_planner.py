from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional


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
    """
    單一步驟。

    這一層先不直接綁死 MCP decorator，
    而是用乾淨的步驟資料結構來描述：
    - 要做什麼
    - 為什麼做
    - 需要什麼參數
    """

    step_type: PlanStepType
    reason: str
    args: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionPlan:
    """
    一份可執行的計畫。

    intent:
        使用者這句話想做的事

    mode:
        read_only  → 只分析，不修改
        safe_edit  → 走 session / sandbox / validation 修改流程
    """

    intent: str
    mode: Literal["read_only", "safe_edit"]
    summary: str
    steps: List[PlanStep] = field(default_factory=list)


class AgentPlanner:
    """
    正式版 agent brain 的第一版。

    這一層的責任不是直接改檔，
    而是把「使用者的人話需求」先整理成可執行步驟。

    你可以把它想成：
        使用者說人話
            ↓
        AgentPlanner 先想清楚
            ↓
        再交給工具層去做
    """

    def build_plan(
        self,
        *,
        intent: str,
        user_request: str,
        repo_root: str,
        relative_path: str = "README.md",
        content: str = "pipeline test",
        mode: str = "append",
        old_text: Optional[str] = None,
        operations: Optional[List[dict[str, Any]]] = None,
    ) -> ExecutionPlan:
        """
        根據 intent 產生可執行計畫。

        第一版先做穩，不追求花俏：
        - 分析類 → 只讀計畫
        - 修改類 → 安全修改計畫
        - 驗證 / 回滾 → 專用流程
        """
        if intent in {"project_analysis", "code_explanation", "patch_planning", "unknown"}:
            return ExecutionPlan(
                intent=intent,
                mode="read_only",
                summary="先用唯讀方式理解 repo，避免在分析時誤改檔案。",
                steps=[
                    PlanStep(
                        step_type="analyze_repo",
                        reason="先看整體專案結構，建立上下文。",
                        args={"repo_root": repo_root},
                    ),
                    PlanStep(
                        step_type="find_entrypoints",
                        reason="找可能的入口點，幫助後續理解流程。",
                        args={"repo_root": repo_root},
                    ),
                ],
            )

        if intent == "patch_apply":
            plan_steps: List[PlanStep] = [
                PlanStep(
                    step_type="create_task_session",
                    reason="先建立獨立 session，確保修改在隔離環境進行。",
                    args={"repo_root": repo_root},
                ),
            ]

            if operations:
                for operation in operations:
                    plan_steps.append(
                        PlanStep(
                            step_type="edit_file",
                            reason="依照規劃逐步修改 sandbox 內的檔案。",
                            args={
                                "relative_path": operation.get("relative_path", relative_path),
                                "content": operation.get("content", content),
                                "mode": operation.get("mode", mode),
                                "old_text": operation.get("old_text"),
                            },
                        )
                    )
            else:
                plan_steps.append(
                    PlanStep(
                        step_type="edit_file",
                        reason="先套用這次指定的修改。",
                        args={
                            "relative_path": relative_path,
                            "content": content,
                            "mode": mode,
                            "old_text": old_text,
                        },
                    )
                )

            plan_steps.extend(
                [
                    PlanStep(
                        step_type="preview_session_diff",
                        reason="修改後先看差異，確認改到的是對的地方。",
                        args={},
                    ),
                    PlanStep(
                        step_type="run_validation_pipeline",
                        reason="修改後要自動驗證，避免把壞掉的內容留在 session。",
                        args={"repo_root": repo_root},
                    ),
                ]
            )

            return ExecutionPlan(
                intent=intent,
                mode="safe_edit",
                summary="建立安全修改計畫：先建 session，再修改，再看 diff，最後驗證。",
                steps=plan_steps,
            )

        if intent == "validation_only":
            return ExecutionPlan(
                intent=intent,
                mode="read_only",
                summary="這次需求是驗證導向，等待提供 session 後執行驗證。",
                steps=[
                    PlanStep(
                        step_type="respond_read_only",
                        reason="目前缺少 session_id，先回覆需要哪個 session。",
                        args={
                            "message": "validation_only 需要指定 session_id，才能執行驗證。"
                        },
                    )
                ],
            )

        if intent == "rollback":
            return ExecutionPlan(
                intent=intent,
                mode="read_only",
                summary="這次需求是回滾導向，等待提供 session 後執行回滾。",
                steps=[
                    PlanStep(
                        step_type="respond_read_only",
                        reason="目前缺少 session_id，先回覆需要哪個 session。",
                        args={
                            "message": "rollback 需要指定 session_id，才能執行回滾。"
                        },
                    )
                ],
            )

        return ExecutionPlan(
            intent="unknown",
            mode="read_only",
            summary="目前無法安全判斷意圖，先保持唯讀。",
            steps=[
                PlanStep(
                    step_type="respond_read_only",
                    reason="不明確需求先不動檔案。",
                    args={"message": "無法明確判斷需求，先保持唯讀模式。"},
                )
            ],
        )
