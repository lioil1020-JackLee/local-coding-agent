import json

from repo_guardian_mcp.services.agent_session_runtime import AgentSessionRuntime


def test_runtime_runs_analysis_and_persists_agent_session(tmp_path):
    (tmp_path / "README.md").write_text("demo\n", encoding="utf-8")
    runtime = AgentSessionRuntime()

    result = runtime.handle_turn(repo_root=str(tmp_path), raw_text="請分析這個專案")

    assert result.ok is True
    assert result.mode == "run"
    assert result.payload["selected_skill"] == "analyze_repo"
    assert result.payload["agent_session_id"].startswith("agent-")

    session_file = tmp_path / "agent_runtime" / "agent_sessions" / f"{result.agent_session_id}.json"
    data = json.loads(session_file.read_text(encoding="utf-8"))
    assert data["last_analysis"]["selected_skill"] == "analyze_repo"
    assert data["pending_action"] is None


def test_runtime_plan_then_status_is_session_aware(tmp_path):
    (tmp_path / "README.md").write_text("demo\n", encoding="utf-8")
    runtime = AgentSessionRuntime()

    planned = runtime.handle_turn(repo_root=str(tmp_path), raw_text="請幫我修改 README")
    status = runtime.handle_turn(
        repo_root=str(tmp_path),
        raw_text="/status",
        agent_session_id=planned.agent_session_id,
    )

    assert planned.ok is True
    assert planned.mode == "plan"
    assert planned.payload["pending_action"] == "apply"
    assert planned.payload["selected_skill"] == "safe_edit"

    assert status.ok is True
    assert status.mode == "status"
    assert status.payload["pending_action"] == "apply"
    assert status.payload["selected_skill"] == "safe_edit"
    assert status.payload["current_plan"]["selected_skill"] == "safe_edit"
