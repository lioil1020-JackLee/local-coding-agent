from repo_guardian_mcp.services.cli_chat_service import CLIChatService
from repo_guardian_mcp.services.trace_summary_service import TraceSummaryService


class _DummyResult:
    def __init__(self, payload):
        self.ok = True
        self.mode = "run"
        self.message = "已執行 repo 分析並寫入 session。"
        self.agent_session_id = "agent-test"
        self.payload = payload


class _DummyRuntime:
    def __init__(self):
        self.trace_summary_service = TraceSummaryService()

    def handle_turn(self, **kwargs):
        payload = {
            "trace_summary": {
                "text": "[trace summary]\n- 總步驟：2\n- 成功：2\n- 選擇 技能：成功\n-  驗證結果：成功",
                "items": [
                    {"step_id": "select_skill", "step_type": "select_skill", "status": "success", "retry_count": 0},
                    {"step_id": "validate_skill", "step_type": "validate_skill", "status": "success", "retry_count": 0},
                ],
            },
            "trace_summary_text": "[trace summary]\n- legacy value",
            "display_message": "legacy display",
        }
        canonical_payload = self.trace_summary_service.canonicalize_payload(payload, message="已執行 repo 分析並寫入 session。")
        return _DummyResult(canonical_payload)


def test_cli_chat_uses_runtime_canonical_payload():
    chat = CLIChatService(runtime=_DummyRuntime())
    turn = chat.handle_input(repo_root=".", raw_text="請分析這個專案")

    assert turn.payload["trace_summary_text"] == turn.payload["trace_summary"]["text"]
    assert "選擇 技能" not in turn.payload["display_message"]
    assert "-  驗證結果" not in turn.payload["display_message"]
    assert "驗證結果：成功" in turn.payload["display_message"]
