from repo_guardian_mcp.services.plain_language_understanding_service import PlainLanguageUnderstandingService


def test_plain_language_detects_analysis_first_phrase():
    svc = PlainLanguageUnderstandingService()
    out = svc.interpret("先不要改，先幫我看懂這個專案在做什麼")
    assert out.suggested_intent == "analyze_repo"
    assert out.force_plan_only is False


def test_plain_language_detects_edit_phrase_and_file_path():
    svc = PlainLanguageUnderstandingService()
    out = svc.interpret("幫我改 docs/04_開發流程_協作與進度.md，加上一行說明")
    assert out.suggested_intent == "propose_edit"
    assert out.force_plan_only is True
    assert out.relative_path == "docs/04_開發流程_協作與進度.md"
    assert out.mode == "append"


def test_plain_language_detects_replace_phrase():
    svc = PlainLanguageUnderstandingService()
    out = svc.interpret('幫我把「舊字串」改成「新字串」')
    assert out.suggested_intent == "propose_edit"
    assert out.mode == "replace"
    assert out.old_text == "舊字串"
    assert out.content == "新字串"

