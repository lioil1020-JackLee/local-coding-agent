from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional

from repo_guardian_mcp.services.execution_controller import FallbackPolicy, RetryPolicy, StopPolicy


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
    step_type: PlanStepType
    reason: str
    args: Dict[str, Any] = field(default_factory=dict)
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)
    stop_policy: StopPolicy = field(default_factory=StopPolicy)
    fallback_policies: List[FallbackPolicy] = field(default_factory=list)


@dataclass
class ExecutionPlan:
    intent: str
    mode: Literal["read_only", "safe_edit"]
    summary: str
    steps: List[PlanStep] = field(default_factory=list)


class AgentPlanner:
    """
    把使用者需求整理成可執行步驟。

    這一版開始補：
    - retry policy
    - stop guard
    - fallback policy
    - idempotent edit 預設模式
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
            edit_args = {
                "relative_path": relative_path,
                "content": content,
                "mode": _normalize_edit_mode(mode=mode, old_text=old_text),
                "old_text": old_text,
                "operations": operations,
            }

            return ExecutionPlan(
                intent=intent,
                mode="safe_edit",
                summary="建立安全修改計畫：先建 session，再修改，再看 diff，最後驗證。",
                steps=[
                    PlanStep(
                        step_type="create_task_session",
                        reason="先建立獨立 session，確保修改在隔離環境進行。",
                        args={"repo_root": repo_root},
                        retry_policy=RetryPolicy(max_attempts=2, retry_on_error_codes=("workspace_prepare_failed",)),
                        stop_policy=StopPolicy(stop_on_failure=True),
                    ),
                    PlanStep(
                        step_type="edit_file",
                        reason="套用這次指定的修改，而且預設必須 idempotent。",
                        args=edit_args,
                        retry_policy=RetryPolicy(max_attempts=1),
                        stop_policy=StopPolicy(stop_on_failure=True),
                    ),
                    PlanStep(
                        step_type="preview_session_diff",
                        reason="修改後先看差異，確認改到的是對的地方。",
                        args={},
                        retry_policy=RetryPolicy(max_attempts=2, retry_on_error_codes=("session_not_found",)),
                        stop_policy=StopPolicy(stop_on_failure=True, stop_on_no_change=False),
                    ),
                    PlanStep(
                        step_type="run_validation_pipeline",
                        reason="修改後要自動驗證，避免把壞掉的內容留在 session。",
                        args={"repo_root": repo_root},
                        retry_policy=RetryPolicy(max_attempts=1),
                        stop_policy=StopPolicy(stop_on_failure=True),
                        fallback_policies=[
                            FallbackPolicy(
                                step_type="rollback_session",
                                args={"repo_root": repo_root, "cleanup_workspace": True},
                                reason="驗證失敗時，自動把這次 session 回滾，避免殘留不穩定狀態。",
                            )
                        ],
                    ),
                ],
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
                        args={"message": "validation_only 需要指定 session_id，才能執行驗證。"},
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
                        args={"message": "rollback 需要指定 session_id，才能執行回滾。"},
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


def _normalize_edit_mode(mode: str, old_text: str | None) -> str:
    normalized = (mode or "append_if_missing").strip().lower()
    if normalized == "append":
        return "append_if_missing"
    if normalized == "replace":
        return "replace_once"
    if normalized in {"append_if_missing", "replace_once"}:
        return normalized
    if old_text:
        return "replace_once"
    return "append_if_missing"
