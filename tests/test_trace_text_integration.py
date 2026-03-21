from repo_guardian_mcp.services.trace_summary_service import TraceSummaryService


def test_trace_text_no_spacing_artifacts():
    service = TraceSummaryService()
    summary = service.summarize(
        [
            {"step_id": "select_skill", "step_type": "select_skill", "status": "success"},
            {"step_id": "validate_skill", "step_type": "validate_skill", "status": "success"},
        ]
    )

    text = summary["text"]
    assert "成 功" not in text
    assert "選擇 技能" not in text
    assert "-  " not in text


def test_trace_text_consistency():
    service = TraceSummaryService()
    summary = service.summarize(
        [{"step_id": "finalize", "step_type": "finalize", "status": "success"}]
    )

    assert summary["text"] == service.build_summary_text(summary)


def test_display_message_contains_trace():
    service = TraceSummaryService()
    summary = service.summarize(
        [{"step_id": "execute_skill", "step_type": "execute_skill", "status": "success"}]
    )
    msg = service.build_display_message("已執行 repo 分析並寫入 session。", summary["text"])

    assert "[trace summary]" in msg
    assert "成功" in msg
