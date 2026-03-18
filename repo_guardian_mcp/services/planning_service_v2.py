from __future__ import annotations

from dataclasses import dataclass

from repo_guardian_mcp.services.execution_controller import ExecutionStep


@dataclass(slots=True)
class ExecutionPlan:
    """給 ExecutionController 使用的輕量計畫。"""

    requires_session: bool
    mode: str
    summary: str
    steps: list[ExecutionStep]


class PlanningServiceV2:
    """將自然語言需求轉為可執行步驟。

    這一版刻意維持輕量，先把 modify / read-only 分流做好，
    避免在 controller 還沒穩定前就引入過度複雜的 autonomous planner。
    """

    MODIFY_KEYWORDS = (
        "修改",
        "新增",
        "刪除",
        "重構",
        "refactor",
        "edit",
        "change",
        "write",
        "patch",
    )

    def create_plan(self, user_request: str, repo_root: str | None = None) -> ExecutionPlan:
        request_text = user_request.lower()
        is_modify = any(keyword in request_text for keyword in self.MODIFY_KEYWORDS)

        if not is_modify:
            return ExecutionPlan(
                requires_session=False,
                mode="read_only",
                summary="read-only analysis",
                steps=[
                    ExecutionStep(step_id="step_1", step_type="analyze_repo"),
                    ExecutionStep(step_id="step_2", step_type="summarize_findings"),
                ],
            )

        return ExecutionPlan(
            requires_session=True,
            mode="modify",
            summary="safe edit workflow",
            steps=[
                ExecutionStep(
                    step_id="step_1",
                    step_type="preview_plan",
                    payload={"user_request": user_request},
                ),
                ExecutionStep(
                    step_id="step_2",
                    step_type="create_task_session",
                    payload={"repo_root": repo_root},
                ),
                ExecutionStep(step_id="step_3", step_type="edit_file"),
                ExecutionStep(step_id="step_4", step_type="preview_session_diff"),
                ExecutionStep(
                    step_id="step_5",
                    step_type="run_validation_pipeline",
                    payload={"repo_root": repo_root},
                ),
            ],
        )
