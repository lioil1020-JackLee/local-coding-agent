from dataclasses import dataclass

from repo_guardian_mcp.services.execution_controller import (
    ExecutionController,
    ExecutionPlan,
    ExecutionRequest,
    ExecutionStatus,
    ExecutionStep,
)


class FakePlanner:
    def __init__(self, plan: ExecutionPlan) -> None:
        self.plan = plan

    def build_execution_plan(self, request: ExecutionRequest) -> ExecutionPlan:
        return self.plan


class FakeSessionService:
    def __init__(self, fail_once: bool = False) -> None:
        self.fail_once = fail_once
        self.called = 0

    def create_task_session(self, repo_root: str, metadata: dict | None = None) -> dict:
        self.called += 1
        if self.fail_once and self.called == 1:
            raise RuntimeError("第一次建立 session 失敗")
        return {
            "ok": True,
            "session_id": "session-001",
            "sandbox_path": "/tmp/sandbox-001",
            "repo_root": repo_root,
        }


class FakeEditOrchestrator:
    def __init__(self, edit_ok: bool = True, diff_ok: bool = True) -> None:
        self.edit_ok = edit_ok
        self.diff_ok = diff_ok

    def edit(self, context) -> dict:
        return {
            "ok": self.edit_ok,
            "message": "編輯成功" if self.edit_ok else "編輯失敗",
        }

    def preview_diff(self, context) -> dict:
        return {
            "ok": self.diff_ok,
            "message": "diff 成功" if self.diff_ok else "diff 失敗",
            "diff_text": "--- a\n+++ b\n",
        }


class FakeValidationService:
    def __init__(self, ok: bool = True) -> None:
        self.ok = ok

    def run_validation(self, context) -> dict:
        return {
            "ok": self.ok,
            "message": "驗證通過" if self.ok else "驗證失敗",
        }


class FakeRollbackService:
    def __init__(self, ok: bool = True) -> None:
        self.ok = ok
        self.called = 0

    def rollback_session(self, session_id: str) -> dict:
        self.called += 1
        return {
            "ok": self.ok,
            "message": "已回滾" if self.ok else "回滾失敗",
            "session_id": session_id,
        }


class FakeAnalysisExecutor:
    def analyze(self, context) -> dict:
        return {
            "summary": "分析成功",
            "files": ["README.md"],
        }


def build_edit_plan() -> ExecutionPlan:
    return ExecutionPlan(
        task_type="edit",
        requires_session=True,
        requires_validation=True,
        allow_rollback=True,
        steps=[
            ExecutionStep(name="預覽計畫", action="preview_plan"),
            ExecutionStep(name="建立 session", action="create_session", retry_limit=1),
            ExecutionStep(name="編輯", action="edit"),
            ExecutionStep(name="預覽 diff", action="preview_diff"),
            ExecutionStep(name="驗證", action="validate"),
        ],
    )


def build_analyze_plan() -> ExecutionPlan:
    return ExecutionPlan(
        task_type="analyze",
        steps=[
            ExecutionStep(name="預覽計畫", action="preview_plan"),
            ExecutionStep(name="分析", action="analyze"),
        ],
    )


def test_edit_flow_success() -> None:
    controller = ExecutionController(
        planner=FakePlanner(build_edit_plan()),
        session_service=FakeSessionService(),
        edit_orchestrator=FakeEditOrchestrator(edit_ok=True, diff_ok=True),
        validation_service=FakeValidationService(ok=True),
        rollback_service=FakeRollbackService(ok=True),
        analysis_executor=FakeAnalysisExecutor(),
    )

    result = controller.run(
        ExecutionRequest(
            task_type="edit",
            user_request="請修改 README",
            repo_root="E:/py/local-coding-agent",
        )
    )

    assert result.ok is True
    assert result.status == ExecutionStatus.SUCCESS
    assert result.session_id == "session-001"
    assert any(step.action == "validate" and step.ok for step in result.steps)


def test_create_session_retry_once_then_success() -> None:
    controller = ExecutionController(
        planner=FakePlanner(build_edit_plan()),
        session_service=FakeSessionService(fail_once=True),
        edit_orchestrator=FakeEditOrchestrator(edit_ok=True, diff_ok=True),
        validation_service=FakeValidationService(ok=True),
        rollback_service=FakeRollbackService(ok=True),
        analysis_executor=FakeAnalysisExecutor(),
    )

    result = controller.run(
        ExecutionRequest(
            task_type="edit",
            user_request="請修改 README",
            repo_root="E:/py/local-coding-agent",
        )
    )

    assert result.ok is True
    assert result.status == ExecutionStatus.SUCCESS
    create_steps = [step for step in result.steps if step.action == "create_session"]
    assert create_steps, "應該至少記錄一次 create_session 的最終結果"


def test_edit_failure_should_stop_without_retry() -> None:
    controller = ExecutionController(
        planner=FakePlanner(build_edit_plan()),
        session_service=FakeSessionService(),
        edit_orchestrator=FakeEditOrchestrator(edit_ok=False, diff_ok=True),
        validation_service=FakeValidationService(ok=True),
        rollback_service=FakeRollbackService(ok=True),
        analysis_executor=FakeAnalysisExecutor(),
    )

    result = controller.run(
        ExecutionRequest(
            task_type="edit",
            user_request="請修改 README",
            repo_root="E:/py/local-coding-agent",
        )
    )

    assert result.ok is False
    assert result.status == ExecutionStatus.STOPPED
    assert result.error is not None


def test_validation_failure_should_trigger_rollback() -> None:
    rollback_service = FakeRollbackService(ok=True)

    controller = ExecutionController(
        planner=FakePlanner(build_edit_plan()),
        session_service=FakeSessionService(),
        edit_orchestrator=FakeEditOrchestrator(edit_ok=True, diff_ok=True),
        validation_service=FakeValidationService(ok=False),
        rollback_service=rollback_service,
        analysis_executor=FakeAnalysisExecutor(),
    )

    result = controller.run(
        ExecutionRequest(
            task_type="edit",
            user_request="請修改 README",
            repo_root="E:/py/local-coding-agent",
        )
    )

    assert result.ok is False
    assert result.status == ExecutionStatus.ROLLED_BACK
    assert rollback_service.called == 1


def test_analyze_flow_should_not_create_session() -> None:
    session_service = FakeSessionService()

    controller = ExecutionController(
        planner=FakePlanner(build_analyze_plan()),
        session_service=session_service,
        edit_orchestrator=FakeEditOrchestrator(),
        validation_service=FakeValidationService(ok=True),
        rollback_service=FakeRollbackService(ok=True),
        analysis_executor=FakeAnalysisExecutor(),
    )

    result = controller.run(
        ExecutionRequest(
            task_type="analyze",
            user_request="幫我分析這個專案",
            repo_root="E:/py/local-coding-agent",
        )
    )

    assert result.ok is True
    assert result.status == ExecutionStatus.SUCCESS
    assert session_service.called == 0
    assert result.final_output["analysis"]["summary"] == "分析成功"
