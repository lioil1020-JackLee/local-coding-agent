import json

from repo_guardian_mcp import server


def test_server_handle_request_rejects_invalid_method():
    try:
        server._handle_request({"jsonrpc": "2.0"})
    except server.MCPProtocolError as exc:
        assert exc.code == server.JSONRPC_INVALID_REQUEST
    else:
        raise AssertionError("expected MCPProtocolError")


def test_server_tools_call_requires_valid_params():
    req = {"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "", "arguments": {}}}
    try:
        server._handle_request(req)
    except server.MCPProtocolError as exc:
        assert exc.code == server.JSONRPC_INVALID_PARAMS
    else:
        raise AssertionError("expected MCPProtocolError")


def test_server_tools_call_returns_structured_content():
    req = {
        "jsonrpc": "2.0",
        "id": "1",
        "method": "tools/call",
        "params": {
            "name": "preview_user_request_plan",
            "arguments": {
                "repo_root": ".",
                "user_request": "先幫我分析這個專案",
                "task_type": "auto",
            },
        },
    }
    out = server._handle_request(req)
    assert "content" in out
    assert "structuredContent" in out
    assert out["structuredContent"]["ok"] is True
    assert out["structuredContent"]["tool_name"] == "preview_user_request_plan"
    assert out["structuredContent"]["trace_ref"]
    assert isinstance(out["structuredContent"]["timing_ms"], int)


def test_build_error_response_contains_data():
    out = server._build_error_response(
        request_id="abc",
        code=server.JSONRPC_INVALID_PARAMS,
        message="bad params",
        data={"field": "name"},
    )
    assert out["jsonrpc"] == "2.0"
    assert out["id"] == "abc"
    assert out["error"]["code"] == server.JSONRPC_INVALID_PARAMS
    assert out["error"]["data"]["field"] == "name"
    json.dumps(out, ensure_ascii=False)

