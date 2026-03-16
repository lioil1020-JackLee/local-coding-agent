import json
from pathlib import Path

from repo_guardian_mcp.tools.run_task_pipeline import run_task_pipeline


def test_run_task_pipeline_append_success():
    result = run_task_pipeline(
        repo_root=r"E:\py\local-coding-agent",
        relative_path="README.md",
        content="pytest append line 1\npytest append line 2",
        mode="append",
    )

    assert result["ok"] is True
    assert "session_id" in result
    assert "diff_text" in result
    assert "pytest append line 1" in result["diff_text"]
    assert "pytest append line 2" in result["diff_text"]
    assert result["changed"] is True
    assert "session_file" in result
    assert result["validation"]["passed"] is True
    assert result["validation"]["status"] == "pass"

    session_file = Path(result["session_file"])
    assert session_file.exists()

    data = json.loads(session_file.read_text(encoding="utf-8"))
    assert data["status"] == "validated"
    assert data["changed"] is True
    assert "edited_files" in data
    assert "summary" in data
    assert "validation" in data
    assert data["validation"]["passed"] is True


def test_run_task_pipeline_replace_success():
    result = run_task_pipeline(
        repo_root=r"E:\py\local-coding-agent",
        relative_path="README.md",
        old_text="Repository scaffold for a local coding agent and MCP-style guardian.",
        content="Repository scaffold for a local coding agent / repo guardian MCP.",
        mode="replace",
    )

    assert result["ok"] is True
    assert "session_id" in result
    assert "diff_text" in result
    assert "-Repository scaffold for a local coding agent and MCP-style guardian." in result["diff_text"]
    assert "+Repository scaffold for a local coding agent / repo guardian MCP." in result["diff_text"]
    assert result["changed"] is True
    assert result["validation"]["passed"] is True


def test_run_task_pipeline_multi_operations_success():
    result = run_task_pipeline(
        repo_root=r"E:\py\local-coding-agent",
        operations=[
            {
                "relative_path": "README.md",
                "mode": "replace",
                "old_text": "Repository scaffold for a local coding agent and MCP-style guardian.",
                "content": "Repository scaffold for a local coding agent / repo guardian MCP.",
            },
            {
                "relative_path": "README.md",
                "mode": "append",
                "content": "\npytest multi operation line",
            },
        ],
    )

    assert result["ok"] is True
    assert "session_id" in result
    assert "diff_text" in result
    assert "+Repository scaffold for a local coding agent / repo guardian MCP." in result["diff_text"]
    assert "pytest multi operation line" in result["diff_text"]
    assert result["changed"] is True
    assert result["validation"]["passed"] is True
    assert len(result["edited_files"]) >= 1


def test_run_task_pipeline_file_not_found():
    result = run_task_pipeline(
        repo_root=r"E:\py\local-coding-agent",
        relative_path="NOT_EXIST.md",
        content="pytest line 1\npytest line 2",
        mode="append",
    )

    assert result["ok"] is False
    assert "error" in result
    assert "找不到檔案" in result["error"]


def test_run_task_pipeline_replace_target_not_found():
    result = run_task_pipeline(
        repo_root=r"E:\py\local-coding-agent",
        relative_path="README.md",
        old_text="THIS TEXT DOES NOT EXIST",
        content="new text",
        mode="replace",
    )

    assert result["ok"] is False
    assert "error" in result
    assert "找不到要替換的文字" in result["error"]