from repo_guardian_mcp.utils.text_guard import is_safe_text

def test_text_guard():
    assert is_safe_text('ok')
