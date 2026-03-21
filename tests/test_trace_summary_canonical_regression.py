from repo_guardian_mcp.services.trace_summary_service import TraceSummaryService


def test_trace_summary_text_is_rebuilt_from_items_lines():
    service = TraceSummaryService()
    summary = {
        "total": 5,
        "success": 5,
        "failed": 0,
        "error": 0,
        "skipped": 0,
        "items": [
            {"step_id": "preview_plan", "step_type": "preview_plan", "status": "success", "retry_count": 0, "error": None, "step_label": "預覽 計畫", "line": "- 預覽計畫：成功"},
            {"step_id": "select_skill", "step_type": "select_skill", "status": "success", "retry_count": 0, "error": None, "step_label": "選擇 技能", "line": "- 選擇技能：成功"},
            {"step_id": "execute_skill", "step_type": "execute_skill", "status": "success", "retry_count": 0, "error": None, "step_label": "執行技能", "line": "- 執行技能：成功"},
            {"step_id": "validate_skill", "step_type": "validate_skill", "status": "success", "retry_count": 0, "error": None, "step_label": "驗證結果", "line": "- 驗證結果：成功"},
            {"step_id": "finalize", "step_type": "finalize", "status": "success", "retry_count": 0, "error": None, "step_label": "整理輸出", "line": "- 整理輸出：成功"},
        ],
        "text": "[trace summary]\n- 驗證結果：成 功",
    }
    canonical = service.canonicalize_trace_summary(summary)
    assert canonical["text"] == (
        "[trace summary]\n"
        "- 總步驟：5\n"
        "- 成功：5\n"
        "- 失敗：0\n"
        "- 錯誤：0\n"
        "- 略過：0\n"
        "- 預覽計畫：成功\n"
        "- 選擇技能：成功\n"
        "- 執行技能：成功\n"
        "- 驗證結果：成功\n"
        "- 整理輸出：成功"
    )
