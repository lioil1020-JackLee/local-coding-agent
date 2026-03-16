from repo_guardian_mcp.tools.get_session_status import get_session_status
from repo_guardian_mcp.tools.run_task_pipeline import run_task_pipeline


def test_get_session_status_success():
    run_result = run_task_pipeline(
        repo_root=r"E:\py\local-coding-agent",
        relative_path="README.md",
        content="status check line",
        mode="append",
    )

    assert run_result["ok"] is True

    session_id = run_result["session_id"]
    result = get_session_status(
        repo_root=r"E:\py\local-coding-agent",
        session_id=session_id,
    )

    assert result["ok"] is True
    assert result["session_id"] == session_id
    assert result["status"] == "validated"
    assert result["changed"] is True
    assert "edited_files" in result
    assert "summary" in result
    assert "validation" in result
    assert result["validation"]["passed"] is True


def test_get_session_status_not_found():
    result = get_session_status(
        repo_root=r"E:\py\local-coding-agent",
        session_id="not_exist_session_id",
    )

    assert result["ok"] is False
    assert "error" in result
    assert "找不到 session 檔案" in result["error"]