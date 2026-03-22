import json

from repo_guardian_mcp.services.continue_e2e_service import ContinueE2EService


def test_continue_e2e_service_run(tmp_path):
    (tmp_path / "README.md").write_text("demo\n", encoding="utf-8")
    svc = ContinueE2EService()
    out = svc.run(repo_root=str(tmp_path))
    assert out["ok"] is True
    assert out["check_count"] >= 5
    assert isinstance(out["checks"], list)
    assert out["user_friendly_summary"]
    json.dumps(out, ensure_ascii=False)
