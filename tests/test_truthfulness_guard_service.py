from __future__ import annotations

from repo_guardian_mcp.services.truthfulness_guard_service import TruthfulnessGuardService


def test_truth_guard_enforce_adds_alternatives_on_failure() -> None:
    service = TruthfulnessGuardService()
    out = service.enforce(
        user_request="請分析完成度",
        payload={"ok": False, "summary": "已完成"},
    )
    review = out["truthfulness_review"]
    assert review["passed"] is False
    assert isinstance(out.get("next_actions"), list)
    assert len(out["next_actions"]) >= 1
    assert "truthful_disclosure" in out


def test_truth_guard_passes_when_evidence_exists() -> None:
    service = TruthfulnessGuardService()
    out = service.enforce(
        user_request="請分析專案",
        payload={
            "ok": True,
            "summary": "完成度約 80%",
            "python_evidence": [{"path": "app/main.py"}],
            "next_actions": ["繼續看 app/"],
        },
    )
    assert out["truthfulness_review"]["passed"] is True
