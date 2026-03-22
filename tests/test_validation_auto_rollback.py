import repo_guardian_mcp.tools.run_validation_pipeline as pipeline_module


def test_validation_pipeline_auto_rollback_on_fail(monkeypatch):
    monkeypatch.setattr(
        pipeline_module,
        "preview_session_diff",
        lambda session_id: {"ok": True, "diff_text": "+ TODO: this should fail"},
    )
    monkeypatch.setattr(
        pipeline_module,
        "run_validation_hook",
        lambda diff_text: {"passed": False, "status": "fail", "checks": [], "summary": "Validation failed."},
    )
    monkeypatch.setattr(
        pipeline_module,
        "rollback_session",
        lambda repo_root, session_id, cleanup_workspace=True: {"ok": True, "session_id": session_id, "status": "rolled_back"},
    )
    monkeypatch.setattr(
        pipeline_module,
        "update_session_file",
        lambda repo_root, session_id, updates: "mock-session-file.json",
    )

    result = pipeline_module.run_validation_pipeline(repo_root=".", session_id="sess-001", auto_rollback_on_fail=True)

    assert result["ok"] is True
    assert result["status"] == "rolled_back"
    assert result["rollback"]["ok"] is True
    assert result["auto_rollback_on_fail"] is True
