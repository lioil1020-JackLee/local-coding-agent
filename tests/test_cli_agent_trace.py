from repo_guardian_mcp.cli_chat_service import CLIChatService

def test_trace_visible():
    service = CLIChatService()
    res = service.handle_input(".", "請分析 repo")
    assert res["ok"] is True
    assert "trace" in res
    assert len(res["trace"]) >= 1

def test_status_returns_last_trace():
    service = CLIChatService()
    service.handle_input(".", "請分析 repo")
    status = service.handle_input(".", "/status")
    assert status["ok"] is True
    assert "last_trace" in status
    assert len(status["last_trace"]) >= 1