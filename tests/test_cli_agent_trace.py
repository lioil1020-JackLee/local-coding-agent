from repo_guardian_mcp.services.cli_chat_service import CLIChatService


def test_trace_visible():
    service = CLIChatService()
    result = service.handle_input(".", "請分析 repo")

    assert result.ok is True
    assert result.payload.get("agent_session_id")
    assert result.payload.get("display_message")
    assert "trace_summary" in result.payload


def test_status_returns_agent_session_context():
    service = CLIChatService()
    service.handle_input(".", "請分析 repo")
    status = service.handle_input(".", "/status")

    assert status.ok is True
    assert status.mode == "status"
    assert status.payload.get("agent_session_id")
