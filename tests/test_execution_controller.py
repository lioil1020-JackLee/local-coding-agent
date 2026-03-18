from __future__ import annotations

from repo_guardian_mcp.services.execution_controller import (
    ExecutionContext,
    ExecutionController,
    ExecutionStep,
    FallbackPolicy,
    RetryPolicy,
    StepResult,
    StepStatus,
)


class DummyHandler:
    def __init__(self) -> None:
        self._attempts: dict[str, int] = {}

    def can_handle(self, step_type: str) -> bool:
        return step_type in {"ok", "retry_once", "fail", "fallback", "recover"}

    def run(self, step: ExecutionStep, ctx: ExecutionContext) -> StepResult:
        attempt = self._attempts.get(step.step_id, 0)
        self._attempts[step.step_id] = attempt + 1

        if step.step_type == "ok":
            return StepResult(status=StepStatus.SUCCESS, output={"value": step.step_id})

        if step.step_type == "retry_once":
            if attempt == 0:
                return StepResult(status=StepStatus.FAILED, error="temporary")
            return StepResult(status=StepStatus.SUCCESS, output={"retried": True})

        if step.step_type == "fail":
            return StepResult(status=StepStatus.FAILED, error="boom")

        if step.step_type == "fallback":
            return StepResult(status=StepStatus.FAILED, error="need fallback")

        if step.step_type == "recover":
            return StepResult(status=StepStatus.SUCCESS, output={"recovered": True})

        raise AssertionError("unexpected step type")


class DummyFallbackPolicy(FallbackPolicy):
    def get_fallback_steps(self, step: ExecutionStep, result: StepResult) -> list[ExecutionStep]:
        if step.step_type != "fallback":
            return []
        return [ExecutionStep(step_id="recover_1", step_type="recover")]


def test_execution_controller_records_trace_and_state() -> None:
    controller = ExecutionController(handlers=[DummyHandler()])
    ctx = ExecutionContext(task_id="task-1", user_request="test")

    result_ctx = controller.execute(
        steps=[ExecutionStep(step_id="step_1", step_type="ok")],
        ctx=ctx,
    )

    assert result_ctx.state["step_1"] == {"value": "step_1"}
    assert len(result_ctx.trace) == 1
    assert result_ctx.trace[0].status == StepStatus.SUCCESS


def test_execution_controller_supports_retry() -> None:
    controller = ExecutionController(
        handlers=[DummyHandler()],
        retry_policy=RetryPolicy(per_step_max_retries={"retry_once": 1}),
    )
    ctx = ExecutionContext(task_id="task-2", user_request="retry")

    result_ctx = controller.execute(
        steps=[ExecutionStep(step_id="step_retry", step_type="retry_once")],
        ctx=ctx,
    )

    assert result_ctx.state["step_retry"] == {"retried": True}
    assert len(result_ctx.trace) == 2
    assert result_ctx.trace[-1].status == StepStatus.SUCCESS
    assert result_ctx.trace[-1].retry_count == 1


def test_execution_controller_supports_fallback() -> None:
    controller = ExecutionController(
        handlers=[DummyHandler()],
        fallback_policy=DummyFallbackPolicy(),
    )
    ctx = ExecutionContext(task_id="task-3", user_request="fallback")

    result_ctx = controller.execute(
        steps=[ExecutionStep(step_id="step_fallback", step_type="fallback")],
        ctx=ctx,
    )

    assert result_ctx.state["recover_1"] == {"recovered": True}
    assert [item.step_id for item in result_ctx.trace] == ["step_fallback", "recover_1"]
