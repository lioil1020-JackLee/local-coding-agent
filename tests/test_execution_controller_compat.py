from repo_guardian_mcp.services.execution_controller import (
    ExecutionContext,
    ExecutionController,
    ExecutionPlan,
    ExecutionStep,
    FailureKind,
    StepResult,
    StepStatus,
)


class DummyHandler:
    STEP_TYPES = {"edit_file"}

    def handle(self, step, ctx):
        return StepResult(
            status=StepStatus.SUCCESS,
            output={"session_id": "sess-1", "handled": step.step_type},
        )


def test_execution_controller_supports_v1_symbols_and_handle_alias():
    controller = ExecutionController({"edit_file": DummyHandler()})
    plan = ExecutionPlan(steps=[ExecutionStep(step_id="s1", step_type="edit_file")])
    ctx = controller.execute_plan(plan, ExecutionContext(task_id="t1"))

    assert ctx.session_id == "sess-1"
    assert ctx.trace[0].status == StepStatus.SUCCESS
    assert FailureKind.UNKNOWN.value == "unknown"
