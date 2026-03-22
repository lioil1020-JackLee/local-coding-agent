from __future__ import annotations

from repo_guardian_mcp.services.response_quality_gate_service import ResponseQualityGateService


def test_quality_gate_passes_with_evidence_and_actions() -> None:
    service = ResponseQualityGateService()
    report = service.evaluate(
        user_request="請分析整個專案並告訴我完成度",
        payload={
            "completion_estimate": {"score": 72},
            "python_evidence": [{"path": "app/main.py"}],
            "next_actions": ["先看 main.py"],
            "summary": "完成度約 72%",
        },
        profile={"prefer_plain_language": True},
    )
    assert report["passed"] is True
    assert report["score"] >= 70


def test_quality_gate_fails_when_empty() -> None:
    service = ResponseQualityGateService()
    report = service.evaluate(
        user_request="請分析專案完成度",
        payload={"summary": "ok"},
        profile={"prefer_plain_language": True},
    )
    assert report["passed"] is False
    assert "has_evidence" in report["failed_checks"]
