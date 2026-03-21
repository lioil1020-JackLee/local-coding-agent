from repo_guardian_mcp.services.trace_summary_service import TraceSummaryService


def test_trace_summary_text_and_display_are_canonical():
    service = TraceSummaryService()
    summary = service.canonicalize_trace_summary(
        {
            "total": 5,
            "success": 5,
            "failed": 0,
            "error": 0,
            "skipped": 0,
            "items": [
                {"step_id": "preview_plan", "step_type": "preview_plan", "status": "success", "retry_count": 0, "error": None, "step_label": "預覽 計畫", "line": "- 預覽 計畫：成 功"},
                {"step_id": "select_skill", "step_type": "select_skill", "status": "success", "retry_count": 0, "error": None, "step_label": "選擇 技能", "line": "- 選擇 技能：成 功"},
                {"step_id": "execute_skill", "step_type": "execute_skill", "status": "success", "retry_count": 0, "error": None, "step_label": "執行 技能", "line": "- 執行 技能：成 功"},
                {"step_id": "validate_skill", "step_type": "validate_skill", "status": "success", "retry_count": 0, "error": None, "step_label": "驗證 結果", "line": "-  驗證結果：成 功"},
                {"step_id": "finalize", "step_type": "finalize", "status": "success", "retry_count": 0, "error": None, "step_label": "整理 輸出", "line": "- 整理 輸出：成 功"},
            ],
            "text": "[trace summary]\\n- 驗證結果：成 功",
        }
    )

    assert "成 功" not in summary["text"]
    assert "-  驗證結果" not in summary["text"]
    assert "驗證結果：成功" in summary["text"]
    display_message = service.build_display_message("已執行 repo 分析並寫入 session。", summary["text"])
    assert display_message.endswith(summary["text"])
