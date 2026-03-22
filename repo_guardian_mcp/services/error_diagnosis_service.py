from __future__ import annotations

from typing import Any


class ErrorDiagnosisService:
    """Classify failures into stable categories with actionable recovery hints."""

    _HINTS = {
        "user_input_error": "輸入參數可能不完整或格式不對，先補齊必要欄位。",
        "routing_error": "系統無法穩定判斷你要分析還是修改，建議先明確指定 task-type。",
        "execution_error": "任務在執行階段失敗，建議先看 trace 與最近一次輸出。",
        "validation_error": "修改後驗證沒通過，請先看 diff 與驗證訊息，再決定要修正或回滾。",
        "unknown_error": "錯誤類型暫時無法判定，建議先保留 trace_ref 供排查。",
    }

    _RECOVERY_ACTIONS = {
        "user_input_error": [
            "確認 repo_root、prompt、session_id 是否有填。",
            "若是修改任務，補上 relative_path 與 content。",
            "先用 plan 看系統理解是否正確，再執行 run。",
        ],
        "routing_error": [
            "把需求改成一句更明確的話（例如：先分析，不要改檔）。",
            "暫時改用 --task-type analyze 或 --task-type edit。",
            "需要時可加 --skill 指定技能，避免誤路由。",
        ],
        "execution_error": [
            "先看 trace_summary / standardized_trace 找失敗步驟。",
            "若是 bridge 任務，先跑 bridge diagnose。",
            "確認檔案權限與路徑是否可讀寫。",
        ],
        "validation_error": [
            "先看 diff 確認改動是否符合預期。",
            "查看 validation 訊息，修正後再跑一次。",
            "若要快速回復，先執行 rollback。",
        ],
        "unknown_error": [
            "保留 trace_ref 與錯誤訊息。",
            "先用 plan 重跑一次，確認需求理解。",
            "必要時改成分步執行（plan -> run -> diff）。",
        ],
    }

    _RECOMMENDED_COMMANDS = {
        "user_input_error": [
            "uv run repo-guardian plan . --prompt \"請先分析這個專案\" --task-type analyze",
            "uv run repo-guardian run . --prompt \"幫我修改 README\" --task-type edit --relative-path README.md --content \"新增一行\"",
        ],
        "routing_error": [
            "uv run repo-guardian run . --prompt \"先分析這個專案，不要改檔\" --task-type analyze",
            "uv run repo-guardian run . --prompt \"幫我修改 README\" --task-type edit",
        ],
        "execution_error": [
            "uv run repo-guardian bridge diagnose . <task_id>",
            "uv run repo-guardian health report .",
        ],
        "validation_error": [
            "uv run repo-guardian diff . <session_id>",
            "uv run repo-guardian rollback . <session_id>",
        ],
        "unknown_error": [
            "uv run repo-guardian plan . --prompt \"請先幫我分析這個專案\" --task-type analyze",
            "uv run repo-guardian observe routing .",
        ],
    }

    def classify(self, *, error: str | None, payload: dict[str, Any] | None = None) -> str:
        text = str(error or "").lower()
        payload = dict(payload or {})

        if "validation" in text or bool((payload.get("skill_validation") or {}).get("passed") is False):
            return "validation_error"
        if any(token in text for token in ("session_id", "unknown command", "must be", "required", "invalid", "missing")):
            return "user_input_error"
        if any(token in text for token in ("skill", "routing", "intent", "no skill")):
            return "routing_error"
        if error:
            return "execution_error"
        return "unknown_error"

    def build_error_block(self, *, error: str | None, payload: dict[str, Any] | None = None) -> dict[str, Any] | None:
        if not error:
            return None
        code = self.classify(error=error, payload=payload)
        return {
            "code": code,
            "message": error,
            "hint": self._HINTS.get(code, self._HINTS["unknown_error"]),
            "recovery_actions": list(self._RECOVERY_ACTIONS.get(code, self._RECOVERY_ACTIONS["unknown_error"])),
            "recommended_commands": list(self._RECOMMENDED_COMMANDS.get(code, self._RECOMMENDED_COMMANDS["unknown_error"])),
        }
