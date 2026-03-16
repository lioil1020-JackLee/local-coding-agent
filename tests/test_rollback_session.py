from repo_guardian_mcp.tools.get_session_status import get_session_status
from repo_guardian_mcp.tools.rollback_session import rollback_session
from repo_guardian_mcp.tools.run_task_pipeline import run_task_pipeline


REPO_ROOT = r"E:\py\local-coding-agent"


def test_rollback_session_success():
    run_result = run_task_pipeline(
        repo_root=REPO_ROOT,
        relative_path="README.md",
        content="rollback pipeline line",
        mode="append",
    )

    assert run_result["ok"] is True

    session_id = run_result["session_id"]
    rollback_result = rollback_session(
        repo_root=REPO_ROOT,
        session_id=session_id,
    )

    assert rollback_result["ok"] is True
    assert rollback_result["status"] == "rolled_back"

    status_result = get_session_status(
        repo_root=REPO_ROOT,
        session_id=session_id,
    )

    assert status_result["ok"] is True
    assert status_result["status"] == "rolled_back"
