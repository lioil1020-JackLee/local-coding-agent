
from repo_guardian_mcp.agent_loop import AgentLoop


def test_agent_detect_analyze():
    loop = AgentLoop()
    result = loop.run("幫我分析這個 repo")
    assert result["mode"] == "analyze"


def test_agent_detect_edit():
    loop = AgentLoop()
    result = loop.run("幫我修改 README")
    assert result["mode"] == "edit"


def test_agent_chat_fallback():
    loop = AgentLoop()
    result = loop.run("這個專案在幹嘛")
    assert "mode" in result
