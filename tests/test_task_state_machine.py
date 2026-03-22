from repo_guardian_mcp.services.task_state_machine import TaskState, TaskStateMachine


def test_task_state_machine_core_transitions() -> None:
    machine = TaskStateMachine()
    assert machine.transition(previous=None, event="plan", ok=True).current == TaskState.PLANNED
    assert machine.transition(previous=TaskState.PLANNED, event="run", ok=True).current == TaskState.VALIDATED
    assert machine.transition(previous=TaskState.RUNNING, event="run", ok=False).current == TaskState.FAILED


def test_task_state_machine_rollback_from_payload() -> None:
    machine = TaskStateMachine()
    out = machine.transition_from_payload(
        previous=TaskState.RUNNING,
        event="rollback",
        ok=True,
        payload={"status": "rolled_back"},
    )
    assert out.current == TaskState.ROLLED_BACK

