from __future__ import annotations

from repo_guardian_mcp.services.execution_controller import (
    ExecutionController,
    ExecutionStep,
    FailureKind,
    FallbackPolicy,
    RetryPolicy,
    StepResult,
    StepStatus,
)


class TransientToolError(RuntimeError):
    pass


def test_execution_controller_success_trace_and_state_updates() -> None:
    controller = ExecutionController(name="pytest_controller")

    def step_prepare(ctx):
        return StepResult(
            status=StepStatus.SUCCESS,
            summary="prepared",
            updates={"session_id": "s123", "edited_files": []},
        )

    def step_append_trace(ctx):
        edited = list(ctx.state["edited_files"])
        edited.append("README.md")
        return {
            "status": "success",
            "summary": "edited",
            "updates": {"edited_files": edited, "changed": True},
        }

    result = controller.run(
        [
            ExecutionStep(name="prepare", handler=step_prepare),
            ExecutionStep(name="edit", handler=step_append_trace),
        ]
    )

    assert result.ok is True
    assert result.state["session_id"] == "s123"
    assert result.state["changed"] is True
    assert result.state["edited_files"] == ["README.md"]
    assert [item["name"] for item in result.trace] == ["prepare", "edit"]


def test_execution_controller_retry_guard() -> None:
    controller = ExecutionController()
    attempts = {"count": 0}

    def flaky_step(_ctx):
        attempts["count"] += 1
        if attempts["count"] < 2:
            raise TransientToolError("temporary diff failure")
        return StepResult(status=StepStatus.SUCCESS, summary="recovered")

    result = controller.run(
        [
            ExecutionStep(
                name="preview_diff",
                handler=flaky_step,
                retry=RetryPolicy(
                    max_attempts=2,
                    retry_on_kinds=(FailureKind.TRANSIENT,),
                    retry_on_exceptions=(TransientToolError,),
                ),
            )
        ]
    )

    assert result.ok is True
    assert attempts["count"] == 2
    assert len(result.trace) == 2
    assert result.trace[0]["status"] == "error"
    assert result.trace[1]["status"] == "success"


def test_execution_controller_stop_guard() -> None:
    controller = ExecutionController()

    def validation_step(_ctx):
        return StepResult(
            status=StepStatus.ERROR,
            summary="validation failed",
            failure_kind=FailureKind.VALIDATION,
        )

    result = controller.run([ExecutionStep(name="validate", handler=validation_step)])

    assert result.ok is False
    assert result.status.value == "stopped"
    assert result.failed_step == "validate"
    assert result.stop_reason == FailureKind.VALIDATION.value


def test_execution_controller_fallback_policy() -> None:
    controller = ExecutionController()

    def primary(_ctx):
        return StepResult(
            status=StepStatus.ERROR,
            summary="tooling error",
            failure_kind=FailureKind.TOOLING,
        )

    def fallback(ctx):
        return StepResult(
            status=StepStatus.SUCCESS,
            summary="fallback done",
            updates={"fallback_used": True},
        )

    result = controller.run(
        [
            ExecutionStep(
                name="preview_diff",
                handler=primary,
                fallback=FallbackPolicy(enabled=True, fallback_step_names=("preview_diff_py",)),
            ),
            ExecutionStep(name="preview_diff_py", handler=fallback),
        ]
    )

    # 預期 primary 失敗後會 stop，trace 中會留下 fallback 啟動紀錄；
    # 真正接管整體流程時，orchestrator 可以根據 trace/state 決定是否繼續。
    assert result.ok is False
    assert result.failed_step == "preview_diff"
    assert any(item["status"] == "fallback" for item in result.trace)
