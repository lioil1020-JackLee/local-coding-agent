from repo_guardian_mcp.services.validation_service import validate_patch

def test_validate():
    assert validate_patch({'patch': True})['valid'] is True
