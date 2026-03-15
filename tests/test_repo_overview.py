from repo_guardian_mcp.tools.repo_overview import run

def test_overview():
    assert isinstance(run('.'), dict)
