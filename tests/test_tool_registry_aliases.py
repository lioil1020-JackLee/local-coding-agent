from repo_guardian_mcp.tool_registry import get_tool, list_tools


def test_repo_guardian_alias_tools_are_registered():
    names = list_tools()
    assert "preview_user_request_plan" in names
    assert "repo_guardian_preview_user_request_plan_tool" in names
    assert "repo_guardian_handle_user_request_tool" in names
    assert "repo_guardian_edit_file_tool" in names


def test_alias_and_short_name_resolve_same_callable():
    short_fn = get_tool("preview_user_request_plan")
    alias_fn = get_tool("repo_guardian_preview_user_request_plan_tool")
    assert short_fn.__name__ == alias_fn.__name__
    assert short_fn.__module__ == alias_fn.__module__

