from repo_guardian_mcp.services.error_diagnosis_service import ErrorDiagnosisService


def test_error_diagnosis_block_includes_actionable_commands():
    svc = ErrorDiagnosisService()
    out = svc.build_error_block(error="validation failed: command exited 1", payload={"skill_validation": {"passed": False}})
    assert out is not None
    assert out["code"] == "validation_error"
    assert isinstance(out["recovery_actions"], list)
    assert len(out["recovery_actions"]) >= 1
    assert isinstance(out["recommended_commands"], list)
    assert len(out["recommended_commands"]) >= 1


def test_error_diagnosis_classify_user_input():
    svc = ErrorDiagnosisService()
    code = svc.classify(error="missing required session_id", payload={})
    assert code == "user_input_error"

