import json

from repo_guardian_mcp.skills import AnalyzeRepoSkill, SafeEditSkill, SkillManifest, SkillRegistry, SkillContext


def test_skill_registry_supports_manifest_and_dynamic_registration(tmp_path):
    manifest_path = tmp_path / "explain.json"
    manifest_path.write_text(
        json.dumps(
            {
                "name": "explain_repo",
                "description": "說明 repo 用途",
                "version": "3.0",
                "capabilities": ["explain"],
                "aliases": ["explain"],
                "routing_hints": ["說明", "explain"],
                "enabled": True,
                "can_chain_to": ["analyze_repo"],
                "fallback_skills": ["safe_edit"],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    registry = SkillRegistry([AnalyzeRepoSkill(), SafeEditSkill()])
    registry.register_manifest_file(manifest_path)

    metadata = next(item for item in registry.list_skill_metadata() if item["name"] == "explain_repo")
    assert metadata["manifest_path"] == str(manifest_path.resolve())
    assert metadata["can_chain_to"] == ["analyze_repo"]
    assert metadata["fallback_skills"] == ["safe_edit"]
    assert registry.next_skills("explain_repo")[0].name == "analyze_repo"
    assert registry.fallback_skills_for("explain_repo")[0].name == "safe_edit"


def test_skill_registry_enabled_policy_hides_disabled_skill():
    registry = SkillRegistry([AnalyzeRepoSkill(), SafeEditSkill()])
    assert registry.set_enabled("safe_edit", False) is True

    names = [item["name"] for item in registry.list_skill_metadata()]
    assert "safe_edit" not in names
    ctx = SkillContext(repo_root=".", user_request="analyze repo", task_type="analyze")
    assert registry.choose(ctx).name == "analyze_repo"


def test_skill_registry_plan_exposes_chain_and_fallback_metadata():
    registry = SkillRegistry([AnalyzeRepoSkill(), SafeEditSkill()])
    plan = registry.get("safe_edit").plan(SkillContext(repo_root=".", task_type="edit"))

    assert "analyze_repo" in plan.chain_to
    assert "analyze_repo" in plan.fallback_skills
