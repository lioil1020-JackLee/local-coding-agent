from repo_guardian_mcp.services.cli_agent_service import CLIAgentService


def test_analysis_result_contains_narrative_summary(tmp_path):
    (tmp_path / "README.md").write_text("demo\n", encoding="utf-8")
    services_dir = tmp_path / "repo_guardian_mcp" / "services"
    tools_dir = tmp_path / "repo_guardian_mcp" / "tools"
    tests_dir = tmp_path / "tests"
    services_dir.mkdir(parents=True)
    tools_dir.mkdir(parents=True)
    tests_dir.mkdir(parents=True)
    (services_dir / "runtime.py").write_text("print('runtime')\n", encoding="utf-8")
    (tools_dir / "entry.py").write_text("print('tool')\n", encoding="utf-8")
    (tests_dir / "test_main.py").write_text("def test_demo():\n    assert True\n", encoding="utf-8")

    service = CLIAgentService()
    ctx = service.build_context(repo_root=str(tmp_path), user_request="分析這個 repo", task_type="analyze")
    result = service.run(ctx)

    narrative = result["summary"]["narrative_summary"]
    assert result["narrative_summary"] == narrative
    assert "repo_guardian_mcp/services" in narrative
    assert "repo_guardian_mcp/tools" in narrative
    assert "tests/" in narrative
    assert result["skill_validation"]["passed"] is True
