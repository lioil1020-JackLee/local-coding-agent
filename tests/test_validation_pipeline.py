from repo_guardian_mcp.tools.run_task_pipeline import run_task_pipeline
from repo_guardian_mcp.tools.run_validation_pipeline import run_validation_pipeline


REPO_ROOT = r"E:\py\local-coding-agent"


def test_run_validation_pipeline_success():
    run_result = run_task_pipeline(
        repo_root=REPO_ROOT,
        relative_path="README.md",
        content="validation pipeline line",
        mode="append",
    )

    assert run_result["ok"] is True

    session_id = run_result["session_id"]
    result = run_validation_pipeline(
        repo_root=REPO_ROOT,
        session_id=session_id,
    )

    assert result["ok"] is True
    assert result["session_id"] == session_id
    assert "validation" in result
    assert result["validation"]["passed"] is True
