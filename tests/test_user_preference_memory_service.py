from __future__ import annotations

from repo_guardian_mcp.services.user_preference_memory_service import UserPreferenceMemoryService


def test_preference_memory_updates_and_persists(tmp_path) -> None:
    service = UserPreferenceMemoryService()
    profile = service.update_from_user_request(
        repo_root=str(tmp_path),
        user_request="請用白話、一步一步講，盡量簡短，不要術語，你自己接著做完",
    )

    assert profile["prefer_plain_language"] is True
    assert profile["step_by_step"] is True
    assert profile["response_length"] == "short"
    assert profile["avoid_jargon"] is True
    assert profile["prefer_autonomous_execution"] is True

    reloaded = service.load(repo_root=str(tmp_path))
    assert reloaded["response_length"] == "short"
    assert int((reloaded.get("signals") or {}).get("plain_language") or 0) >= 1


def test_preference_style_hint_contains_user_bias(tmp_path) -> None:
    service = UserPreferenceMemoryService()
    profile = service.update_from_user_request(
        repo_root=str(tmp_path),
        user_request="請詳細一點，還是用白話，不要專有名詞",
    )
    hint = service.build_style_hint(profile=profile)
    assert "白話" in hint
    assert "避免工程術語" in hint
    assert "完整一些" in hint
