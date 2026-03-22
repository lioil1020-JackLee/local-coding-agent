from repo_guardian_mcp.services.session_lifecycle_contract_service import SessionLifecycleContractService
from repo_guardian_mcp.tools.create_task_session import create_task_session


def test_session_lifecycle_contract_list_resume_diff_rollback(tmp_path):
    (tmp_path / "README.md").write_text("before\n", encoding="utf-8")
    created = create_task_session(str(tmp_path), create_workspace=True)
    session_id = created["session_id"]
    sandbox_readme = tmp_path / "agent_runtime" / "sandbox_workspaces" / session_id / "README.md"
    sandbox_readme.write_text("after\n", encoding="utf-8")

    service = SessionLifecycleContractService()
    listed = service.list(repo_root=str(tmp_path))
    resumed = service.resume(repo_root=str(tmp_path), session_id=session_id)
    diffed = service.diff(repo_root=str(tmp_path), session_id=session_id)
    rolled = service.rollback(repo_root=str(tmp_path), session_id=session_id, keep_workspace=False)

    assert listed["ok"] is True
    assert listed["status_code"] == "ok"
    assert resumed["ok"] is True
    assert resumed["task_state"] == "running"
    assert diffed["ok"] is True
    assert diffed["changed_file_count"] >= 1
    assert rolled["ok"] is True
    assert rolled["task_state"] == "rolled_back"

