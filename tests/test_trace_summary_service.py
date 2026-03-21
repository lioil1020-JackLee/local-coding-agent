from repo_guardian_mcp.services.trace_summary_service import TraceSummaryService


def test_trace_summary_service_builds_user_facing_text():
    service = TraceSummaryService()

    summary = service.summarize([
        {"step_id": "preview_plan", "step_type": "preview_plan", "status": "success", "retry_count": 0},
        {"step_id": "execute_skill", "step_type": "execute_skill", "status": "failed", "retry_count": 1, "error": "boom"},
    ])

    assert summary["total"] == 2
    assert summary["success"] == 1
    assert summary["failed"] == 1
    assert summary["text"] == (
        "[trace summary]\n"
        "- 總步驟：2\n"
        "- 成功：1\n"
        "- 失敗：1\n"
        "- 錯誤：0\n"
        "- 略過：0\n"
        "- 預覽計畫：成功\n"
        "- 執行技能：失敗，重試 1 次：boom"
    )


def test_trace_summary_service_normalizes_labels_and_display_message():
    service = TraceSummaryService()

    summary = service.summarize([
        {"step_id": "select_skill", "step_type": "select_skill", "status": "success"},
        {"step_id": "validate_skill", "step_type": "validate_skill", "status": "success"},
    ])

    assert "選擇技能：成功" in summary["text"]
    assert "驗證結果：成功" in summary["text"]
    assert "選擇 技能" not in summary["text"]
    assert "成 功" not in summary["text"]

    display_message = service.build_display_message("已整理目前 agent session 狀態。", summary["text"])
    assert display_message == "已整理目前 agent session 狀態。\n\n" + summary["text"]


def test_trace_summary_service_canonicalizes_text_only_summary():
    service = TraceSummaryService()

    text = service.build_summary_text(
        {
            "text": "[trace summary]\n- 總步驟：2\n- 成功：2\n- 選擇 技能：成 功\n-  驗證結果：成功"
        }
    )

    assert text == (
        "[trace summary]\n"
        "- 總步驟：2\n"
        "- 成功：2\n"
        "- 選擇技能：成功\n"
        "- 驗證結果：成功"
    )


def test_trace_summary_service_canonicalize_payload_overwrites_legacy_fields():
    service = TraceSummaryService()

    payload = {
        "trace_summary": {
            "items": [
                {
                    "step_id": "preview_plan",
                    "step_type": "preview_plan",
                    "status": "success",
                    "retry_count": 0,
                    "error": None,
                    "step_label": "預覽 計畫",
                    "line": "- 預覽 計畫：成 功",
                }
            ],
            "text": "[trace summary]\n- 預覽 計畫：成 功",
        },
        "trace_summary_text": "[trace summary]\n- legacy value",
        "display_message": "legacy display",
    }

    canonical = service.canonicalize_payload(payload, message="已執行 repo 分析並寫入 session。")

    assert canonical["trace_summary"]["text"] == canonical["trace_summary_text"]
    assert canonical["display_message"] == "已執行 repo 分析並寫入 session。\n\n" + canonical["trace_summary_text"]
    assert "成 功" not in canonical["trace_summary_text"]
    assert "預覽 計畫" not in canonical["display_message"]
