from __future__ import annotations

from repo_guardian_mcp.services.continue_config_service import ContinueConfigService


def test_continue_config_status_and_sync(tmp_path):
    source_dir = tmp_path / "source_continue"
    source_dir.mkdir()
    target_dir = tmp_path / "target_continue"
    target_dir.mkdir()

    source_cfg = source_dir / "config.yaml"
    target_cfg = target_dir / "config.yaml"
    source_cfg.write_text("name: demo\nversion: 1\n", encoding="utf-8")

    svc = ContinueConfigService()
    before = svc.status(source_config=str(source_cfg), target_config=str(target_cfg))
    assert before["ok"] is True
    assert before["target_exists"] is False
    assert before["same_content"] is False

    out = svc.sync(source_config=str(source_cfg), target_config=str(target_cfg), with_assets=False)
    assert out["ok"] is True
    assert out["same_content"] is True

    after = svc.status(source_config=str(source_cfg), target_config=str(target_cfg))
    assert after["same_content"] is True


def test_continue_config_sync_with_assets(tmp_path):
    source_dir = tmp_path / "source_continue"
    target_dir = tmp_path / "target_continue"
    rules_dir = source_dir / "rules"
    prompts_dir = source_dir / "system-prompts"
    rules_dir.mkdir(parents=True)
    prompts_dir.mkdir(parents=True)
    target_dir.mkdir(parents=True)

    (source_dir / "config.yaml").write_text("name: demo\n", encoding="utf-8")
    (rules_dir / "safe.md").write_text("safe\n", encoding="utf-8")
    (prompts_dir / "planner.md").write_text("plan\n", encoding="utf-8")

    svc = ContinueConfigService()
    out = svc.sync(
        source_config=str(source_dir / "config.yaml"),
        target_config=str(target_dir / "config.yaml"),
        with_assets=True,
    )
    assert out["ok"] is True
    assert sorted(out["copied_assets"]) == ["rules", "system-prompts"]
    assert (target_dir / "rules" / "safe.md").exists()
    assert (target_dir / "system-prompts" / "planner.md").exists()


def test_continue_config_setup_bootstrap_and_backup(tmp_path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    source_dir = repo_root / "continue"
    source_dir.mkdir()
    (source_dir / "config.yaml").write_text("name: repo\n", encoding="utf-8")
    (source_dir / "rules").mkdir()
    (source_dir / "rules" / "safe.md").write_text("safe-new\n", encoding="utf-8")
    (source_dir / "system-prompts").mkdir()
    (source_dir / "system-prompts" / "planner.md").write_text("planner-new\n", encoding="utf-8")

    target_cfg = tmp_path / "target_continue" / "config.yaml"
    target_cfg.parent.mkdir(parents=True)
    target_cfg.write_text("name: old\n", encoding="utf-8")
    (target_cfg.parent / "rules").mkdir()
    (target_cfg.parent / "rules" / "safe.md").write_text("safe-old\n", encoding="utf-8")

    svc = ContinueConfigService()
    out = svc.setup(
        repo_root=str(repo_root),
        source_config="continue/config.yaml",
        target_config=str(target_cfg),
        with_assets=True,
        backup=True,
        dry_run=False,
        run_e2e=False,
    )
    assert out["ok"] is True
    assert out["ready"] is True
    assert out["diagnosis"]["ok"] is True
    assert out["diagnosis"]["ready"] is True
    assert out["diagnosis"]["score"] >= 80
    assert out["status_after"]["same_content"] is True
    assert out["backups"]
    assert target_cfg.read_text(encoding="utf-8") == "name: repo\n"
    assert (target_cfg.parent / "rules" / "safe.md").read_text(encoding="utf-8") == "safe-new\n"
    assert (target_cfg.parent / "system-prompts" / "planner.md").read_text(encoding="utf-8") == "planner-new\n"


def test_continue_config_setup_dry_run(tmp_path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    source_dir = repo_root / "continue"
    source_dir.mkdir()
    (source_dir / "config.yaml").write_text("name: demo\n", encoding="utf-8")

    target_cfg = tmp_path / "target_continue" / "config.yaml"
    target_cfg.parent.mkdir(parents=True)

    svc = ContinueConfigService()
    out = svc.setup(
        repo_root=str(repo_root),
        source_config="continue/config.yaml",
        target_config=str(target_cfg),
        dry_run=True,
    )
    assert out["ok"] is True
    assert out["dry_run"] is True
    assert "diagnosis" in out
    assert target_cfg.exists() is False


def test_continue_config_diagnose_reports_unsynced(tmp_path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    source_dir = repo_root / "continue"
    source_dir.mkdir()
    (source_dir / "config.yaml").write_text("name: new\n", encoding="utf-8")
    (source_dir / "rules").mkdir()
    (source_dir / "rules" / "safe.md").write_text("safe\n", encoding="utf-8")

    target_cfg = tmp_path / "target_continue" / "config.yaml"
    target_cfg.parent.mkdir(parents=True)
    target_cfg.write_text("name: old\n", encoding="utf-8")

    svc = ContinueConfigService()
    diag = svc.diagnose(
        repo_root=str(repo_root),
        source_config="continue/config.yaml",
        target_config=str(target_cfg),
        with_assets=True,
    )
    assert diag["ok"] is True
    assert diag["ready"] is False
    assert diag["score"] < 100
    assert diag["repair_hints"]
    assert diag["recommended_commands"]


def test_continue_config_setup_run_e2e_failure_updates_hint(tmp_path, monkeypatch):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    source_dir = repo_root / "continue"
    source_dir.mkdir()
    (source_dir / "config.yaml").write_text("name: repo\n", encoding="utf-8")

    target_cfg = tmp_path / "target_continue" / "config.yaml"
    target_cfg.parent.mkdir(parents=True)

    class _FakeE2E:
        def run(self, *, repo_root: str) -> dict:
            return {"ok": True, "passed": False, "checks": [{"tool": "demo", "ok": False}]}

    import repo_guardian_mcp.services.continue_e2e_service as e2e_module

    monkeypatch.setattr(e2e_module, "ContinueE2EService", lambda: _FakeE2E())

    svc = ContinueConfigService()
    out = svc.setup(
        repo_root=str(repo_root),
        source_config="continue/config.yaml",
        target_config=str(target_cfg),
        run_e2e=True,
    )
    assert out["ok"] is False
    assert out["ready"] is False
    assert "e2e" in out["next_actions"][0]
    assert "尚未通過" in out["user_friendly_summary"]


def test_continue_config_autofix_repairs_unsynced(tmp_path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    source_dir = repo_root / "continue"
    source_dir.mkdir()
    (source_dir / "config.yaml").write_text("name: source\n", encoding="utf-8")

    target_cfg = tmp_path / "target_continue" / "config.yaml"
    target_cfg.parent.mkdir(parents=True)
    target_cfg.write_text("name: target-old\n", encoding="utf-8")

    svc = ContinueConfigService()
    out = svc.autofix(
        repo_root=str(repo_root),
        source_config="continue/config.yaml",
        target_config=str(target_cfg),
        with_assets=True,
        backup=True,
        dry_run=False,
        run_e2e=False,
    )
    assert out["ok"] is True
    assert out["ready"] is True
    assert out["changed"] is True
    assert out["before"]["ready"] is False
    assert out["after"]["ready"] is True
    assert target_cfg.read_text(encoding="utf-8") == "name: source\n"


def test_continue_config_autofix_noop_when_ready(tmp_path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    source_dir = repo_root / "continue"
    source_dir.mkdir()
    (source_dir / "config.yaml").write_text("name: same\n", encoding="utf-8")

    target_cfg = tmp_path / "target_continue" / "config.yaml"
    target_cfg.parent.mkdir(parents=True)
    target_cfg.write_text("name: same\n", encoding="utf-8")

    svc = ContinueConfigService()
    out = svc.autofix(
        repo_root=str(repo_root),
        source_config="continue/config.yaml",
        target_config=str(target_cfg),
        dry_run=False,
    )
    assert out["ok"] is True
    assert out["ready"] is True
    assert out["changed"] is False
    assert out["applied_actions"] == []


def test_continue_config_autofix_dry_run_no_write(tmp_path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    source_dir = repo_root / "continue"
    source_dir.mkdir()
    (source_dir / "config.yaml").write_text("name: source\n", encoding="utf-8")

    target_cfg = tmp_path / "target_continue" / "config.yaml"
    target_cfg.parent.mkdir(parents=True)
    target_cfg.write_text("name: target-old\n", encoding="utf-8")

    svc = ContinueConfigService()
    out = svc.autofix(
        repo_root=str(repo_root),
        source_config="continue/config.yaml",
        target_config=str(target_cfg),
        dry_run=True,
    )
    assert out["ok"] is True
    assert out["dry_run"] is True
    assert out["changed"] is False
    assert out["planned_actions"] == ["continue_config_setup"]
    assert target_cfg.read_text(encoding="utf-8") == "name: target-old\n"


def test_continue_config_setup_sync_error_triggers_restore(tmp_path, monkeypatch):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    source_dir = repo_root / "continue"
    source_dir.mkdir()
    (source_dir / "config.yaml").write_text("name: source\n", encoding="utf-8")

    target_cfg = tmp_path / "target_continue" / "config.yaml"
    target_cfg.parent.mkdir(parents=True)
    target_cfg.write_text("name: old\n", encoding="utf-8")

    svc = ContinueConfigService()

    def _boom(**_: object) -> dict:
        raise RuntimeError("sync exploded")

    monkeypatch.setattr(svc, "sync", _boom)
    out = svc.setup(
        repo_root=str(repo_root),
        source_config="continue/config.yaml",
        target_config=str(target_cfg),
        backup=True,
        dry_run=False,
    )
    assert out["ok"] is False
    assert out["error_code"] == "sync_failed"
    assert out["rollback"]["attempted"] is True
    assert out["rollback"]["performed"] is True
    assert target_cfg.read_text(encoding="utf-8") == "name: old\n"


def test_continue_config_setup_permission_error_classification(tmp_path, monkeypatch):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    source_dir = repo_root / "continue"
    source_dir.mkdir()
    (source_dir / "config.yaml").write_text("name: source\n", encoding="utf-8")

    target_cfg = tmp_path / "target_continue" / "config.yaml"
    target_cfg.parent.mkdir(parents=True)
    target_cfg.write_text("name: old\n", encoding="utf-8")

    svc = ContinueConfigService()

    def _denied(**_: object) -> dict:
        raise PermissionError("denied")

    monkeypatch.setattr(svc, "sync", _denied)
    out = svc.setup(
        repo_root=str(repo_root),
        source_config="continue/config.yaml",
        target_config=str(target_cfg),
        backup=True,
    )
    assert out["ok"] is False
    assert out["error_code"] == "permission_denied"
    assert out["error_phase"] == "sync"


def test_continue_config_autofix_propagates_setup_error_code(tmp_path, monkeypatch):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    source_dir = repo_root / "continue"
    source_dir.mkdir()
    (source_dir / "config.yaml").write_text("name: source\n", encoding="utf-8")

    target_cfg = tmp_path / "target_continue" / "config.yaml"
    target_cfg.parent.mkdir(parents=True)
    target_cfg.write_text("name: old\n", encoding="utf-8")

    svc = ContinueConfigService()

    def _fake_setup(**_: object) -> dict:
        return {
            "ok": False,
            "error_code": "sync_failed",
            "error_phase": "sync",
            "next_actions": ["please fix"],
        }

    monkeypatch.setattr(svc, "setup", _fake_setup)
    out = svc.autofix(
        repo_root=str(repo_root),
        source_config="continue/config.yaml",
        target_config=str(target_cfg),
        dry_run=False,
    )
    assert out["ok"] is False
    assert out["error_code"] == "sync_failed"
    assert out["error_phase"] == "sync"
