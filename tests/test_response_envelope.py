from repo_guardian_mcp.services.response_envelope_service import ResponseEnvelopeService


def test_response_envelope_contains_stable_contract() -> None:
    service = ResponseEnvelopeService()
    out = service.wrap(
        ok=True,
        mode="run",
        message="done",
        data={"selected_skill": "analyze_repo", "value": 1},
    )
    assert out["ok"] is True
    assert out["mode"] == "run"
    assert out["message"] == "done"
    assert out["error"] is None
    assert out["trace_ref"]
    assert out["task_state"] == "validated"
    assert out["data"]["selected_skill"] == "analyze_repo"
    assert out["data"]["trace_summary"]["total"] >= 1
    assert out["data"]["standardized_trace"][0]["checkpoint"] == 1
    assert out["user_friendly_summary"]
    assert len(out["next_actions"]) >= 1
    assert out["data"]["user_friendly_summary"] == out["user_friendly_summary"]
    # backward-compatible flattened fields
    assert out["selected_skill"] == "analyze_repo"


def test_response_envelope_error_classification() -> None:
    service = ResponseEnvelopeService()
    out = service.wrap(
        ok=False,
        mode="run",
        message="failed",
        data={"skill_validation": {"passed": False}},
        error="validation failed",
    )
    assert out["error"]["code"] == "validation_error"
    assert out["error_code"] == "validation_error"
    assert "hint" in out["error"]
    assert "驗證" in out["user_friendly_summary"]
    assert len(out["next_actions"]) >= 1
