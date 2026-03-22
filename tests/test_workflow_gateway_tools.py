from repo_guardian_mcp.tools.create_task_session import create_task_session
from repo_guardian_mcp.tools.workflow_gateway import (
    edit_file,
    handle_user_request,
    preview_user_request_plan,
)


def test_preview_user_request_plan_analyze(tmp_path):
    (tmp_path / "README.md").write_text("demo\n", encoding="utf-8")
    out = preview_user_request_plan(
        repo_root=str(tmp_path),
        user_request="先幫我分析這個專案，不要改檔",
        task_type="auto",
    )
    assert out["ok"] is True
    assert out["mode"] == "plan"
    assert out["selected_skill"] == "analyze_repo"


def test_handle_user_request_edit_without_apply_returns_plan(tmp_path):
    (tmp_path / "README.md").write_text("demo\n", encoding="utf-8")
    out = handle_user_request(
        repo_root=str(tmp_path),
        user_request="幫我改 README，加上一行",
        task_type="auto",
        apply=False,
    )
    assert out["ok"] is True
    assert out["mode"] == "plan"
    assert out["selected_skill"] == "safe_edit"


def test_handle_user_request_edit_apply_without_content_returns_user_input_error(tmp_path):
    (tmp_path / "README.md").write_text("demo\n", encoding="utf-8")
    out = handle_user_request(
        repo_root=str(tmp_path),
        user_request="幫我改 README",
        task_type="auto",
        apply=True,
    )
    assert out["ok"] is False
    assert out["error"]["code"] == "user_input_error"


def test_handle_user_request_edit_apply_with_content_executes(tmp_path):
    (tmp_path / "README.md").write_text("demo\n", encoding="utf-8")
    out = handle_user_request(
        repo_root=str(tmp_path),
        user_request="幫我改 README",
        task_type="edit",
        apply=True,
        relative_path="README.md",
        content="append-via-gateway",
        mode="append",
    )
    assert out["ok"] is True
    assert out["mode"] == "run"
    assert out["session_id"]


def test_handle_user_request_edit_apply_replace_phrase_executes(tmp_path):
    (tmp_path / "README.md").write_text("old-token\n", encoding="utf-8")
    out = handle_user_request(
        repo_root=str(tmp_path),
        user_request="把「old-token」改成「new-token」",
        task_type="edit",
        apply=True,
        relative_path="README.md",
    )
    assert out["ok"] is True
    assert out["mode"] == "run"
    assert "new-token" in (out.get("diff_text") or "")


def test_edit_file_tool_with_existing_session(tmp_path):
    (tmp_path / "README.md").write_text("before\n", encoding="utf-8")
    created = create_task_session(str(tmp_path), create_workspace=True)
    session_id = created["session_id"]

    out = edit_file(
        repo_root=str(tmp_path),
        session_id=session_id,
        relative_path="README.md",
        content="after-line",
        mode="append",
    )
    assert out["ok"] is True
    assert out["mode"] == "edit"
    assert out["session_id"] == session_id
