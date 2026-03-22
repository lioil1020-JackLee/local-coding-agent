from __future__ import annotations

from typing import Any


class UserFriendlySummaryService:
    """產生給新手看的白話進度摘要與下一步建議。"""

    def build(
        self,
        *,
        mode: str,
        ok: bool,
        message: str,
        task_state: str,
        data: dict[str, Any] | None = None,
        error_code: str | None = None,
    ) -> dict[str, Any]:
        data = dict(data or {})
        selected_skill = data.get("selected_skill")
        session_id = data.get("session_id") or data.get("working_session_id")

        if ok:
            summary = self._success_summary(mode=mode, task_state=task_state, selected_skill=selected_skill, session_id=session_id, message=message)
            next_actions = self._success_next_actions(mode=mode, task_state=task_state, session_id=session_id)
        else:
            summary = self._failure_summary(mode=mode, error_code=error_code, message=message)
            next_actions = self._failure_next_actions(mode=mode, error_code=error_code, session_id=session_id)

        return {
            "user_friendly_summary": summary,
            "next_actions": next_actions,
        }

    def _success_summary(self, *, mode: str, task_state: str, selected_skill: Any, session_id: Any, message: str) -> str:
        if mode == "plan":
            return f"我已先幫你排好執行步驟，現在是規劃完成狀態（{task_state}）。"
        if mode in {"run", "chat"} and str(selected_skill or ""):
            return f"我已完成這次任務，使用的是「{selected_skill}」流程。"
        if mode.startswith("session_"):
            return "我已處理好 session 操作，現在可以繼續下一步。"
        if mode == "rollback":
            return "我已幫你回復到安全狀態。"
        if mode.startswith("benchmark"):
            return "基準測試已完成，你可以直接看成功率。"
        if mode.startswith("observe"):
            return "我已整理好路由觀測資料，方便你看系統是否穩定。"
        if message:
            return message
        return "任務已完成。"

    def _failure_summary(self, *, mode: str, error_code: str | None, message: str) -> str:
        if error_code == "validation_error":
            return "這次修改沒有通過驗證，我已保留可回復的安全流程。"
        if error_code == "user_input_error":
            return "我看不懂部分指令內容，請你再用更白話或補一點細節。"
        if error_code == "routing_error":
            return "我判斷流程時遇到問題，建議你直接說『先分析』或『幫我修改某檔案』。"
        if mode == "rollback":
            return "回滾過程失敗，建議先確認 session 是否存在。"
        return message or "任務失敗，但我有保留錯誤資訊可追蹤。"

    def _success_next_actions(self, *, mode: str, task_state: str, session_id: Any) -> list[str]:
        if mode == "plan":
            return ["如果要正式執行，請輸入 /apply 或 /run。", "如果想先確認風險，可先看 /status。"]
        if mode in {"run", "chat"} and task_state in {"validated", "running"}:
            actions = ["你可以直接繼續下一個需求。", "若要確認細節，可看 trace_summary。"]
            if session_id:
                actions.append("若要看差異可用 /diff。")
            return actions
        if mode == "rollback":
            return ["若要重做修改，建議先用 /plan 重新規劃。"]
        if mode.startswith("benchmark"):
            return ["可執行 benchmark report 查看最新報表。", "目標成功率建議維持在 85% 以上。"]
        return ["你可以繼續下達下一個需求。"]

    def _failure_next_actions(self, *, mode: str, error_code: str | None, session_id: Any) -> list[str]:
        if error_code == "validation_error":
            actions = ["請先看 validation 結果，確認哪個檢查沒過。"]
            if session_id:
                actions.append("必要時可直接 rollback。")
            return actions
        if error_code == "user_input_error":
            return ["請補上檔案路徑或更清楚的目標。", "你也可以先說『先分析不要改』。"]
        if mode == "rollback":
            return ["請先用 session list 確認 session_id。"]
        return ["可先查看 trace_ref 與 error_code，再重試一次。"]

