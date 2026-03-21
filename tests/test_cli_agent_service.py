from repo_guardian_mcp.services.cli_agent_service import CLIAgentService


def test_agent_plan_selects_analysis_skill(tmp_path):
    (tmp_path / "README.md").write_text("demo\n", encoding="utf-8")
    service = CLIAgentService()
    ctx = service.build_context(repo_root=str(tmp_path), user_request="請分析這個專案結構", task_type="analyze")
    result = service.create_plan(ctx)
    assert result["ok"] is True
    assert result["selected_skill"] == "analyze_repo"
    assert "execute_skill" in result["execution_steps"]


def test_agent_run_analysis_success(tmp_path):
    (tmp_path / "README.md").write_text("demo\n", encoding="utf-8")
    service = CLIAgentService()
    ctx = service.build_context(repo_root=str(tmp_path), user_request="分析這個 repo", task_type="analyze")
    result = service.run(ctx)
    assert result["ok"] is True
    assert result["selected_skill"] == "analyze_repo"
    assert result["skill_validation"]["passed"] is True
    assert "README.md" in result["files"]
    assert result["summary"]["repo_name"] == tmp_path.name
    assert result["trace_summary"]["total"] >= 1
    assert "trace summary" in result["trace_summary"]["text"]


def test_agent_run_analysis_ignores_noise_directories(tmp_path):
    (tmp_path / "README.md").write_text("demo\n", encoding="utf-8")
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    (git_dir / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    cache_dir = tmp_path / "__pycache__"
    cache_dir.mkdir()
    (cache_dir / "demo.pyc").write_bytes(b"x")
    sessions_dir = tmp_path / "agent_runtime" / "sessions"
    sessions_dir.mkdir(parents=True)
    (sessions_dir / "123.json").write_text("{}", encoding="utf-8")
    egg_info = tmp_path / "demo.egg-info"
    egg_info.mkdir()
    (egg_info / "PKG-INFO").write_text("demo", encoding="utf-8")

    service = CLIAgentService()
    ctx = service.build_context(repo_root=str(tmp_path), user_request="分析這個 repo", task_type="analyze")
    result = service.run(ctx)

    assert result["ok"] is True
    assert "README.md" in result["files"]
    assert all(not item.startswith(".git/") for item in result["files"])
    assert all("agent_runtime/sessions" not in item for item in result["files"])
    assert all(".egg-info" not in item for item in result["files"])


def test_skill_registry_metadata():
    service = CLIAgentService()
    items = service.skill_registry.list_skill_metadata()
    assert len(items) >= 2
    analyze = next(item for item in items if item["name"] == "analyze_repo")
    assert "repo_analysis" in analyze["capabilities"]
    assert analyze["priority"] == 10


def test_cli_agent_service_run_includes_trace_summary_text(tmp_path):
    from repo_guardian_mcp.services.cli_agent_service import CLIAgentService

    (tmp_path / "README.md").write_text("demo\n", encoding="utf-8")
    service = CLIAgentService()
    ctx = service.build_context(repo_root=str(tmp_path), user_request="請分析這個專案", task_type="analyze")

    result = service.run(ctx)

    assert result["ok"] is True
    assert result["trace_summary_text"] == result["trace_summary"]["text"]
