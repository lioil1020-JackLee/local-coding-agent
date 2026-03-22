from __future__ import annotations

from typing import Any


class ResponseQualityGateService:
    """對輸出做最小品質檢查，避免回覆空泛或過度術語化。"""

    _JARGON_TOKENS = ("orchestrator", "fallback", "contract", "schema", "jsonrpc", "tool_registry")

    def evaluate(
        self,
        *,
        user_request: str,
        payload: dict[str, Any] | None,
        profile: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload = dict(payload or {})
        profile = dict(profile or {})
        checks: list[dict[str, Any]] = []

        has_evidence = bool(
            payload.get("python_evidence")
            or payload.get("entrypoints")
            or payload.get("standardized_trace")
            or payload.get("step_results")
            or payload.get("completion_estimate")
        )
        checks.append(
            {
                "name": "has_evidence",
                "passed": has_evidence,
                "message": "回覆有引用程式碼證據。" if has_evidence else "回覆缺少可驗證的程式碼證據。",
            }
        )

        next_actions = payload.get("next_actions")
        has_next_actions = isinstance(next_actions, list) and len(next_actions) > 0
        checks.append(
            {
                "name": "has_next_actions",
                "passed": has_next_actions,
                "message": "回覆有給下一步。" if has_next_actions else "回覆缺少下一步建議。",
            }
        )

        text = self._collect_text(payload)
        jargon_count = sum(text.lower().count(token) for token in self._JARGON_TOKENS)
        plain_bias = bool(profile.get("prefer_plain_language"))
        plain_ok = jargon_count <= (1 if plain_bias else 3)
        checks.append(
            {
                "name": "plain_language",
                "passed": plain_ok,
                "message": "語氣維持白話。" if plain_ok else "語氣偏術語，需再白話化。",
            }
        )

        need_completion = any(token in (user_request or "") for token in ("完成度", "進度", "百分比"))
        has_completion = ("%" in text) or bool(payload.get("completion_estimate"))
        checks.append(
            {
                "name": "completion_answered",
                "passed": (not need_completion) or has_completion,
                "message": "完成度問題已回覆。" if ((not need_completion) or has_completion) else "使用者問完成度，但回覆缺少完成度資訊。",
            }
        )

        score = 100 - sum(25 for item in checks if not item["passed"])
        score = max(0, min(100, score))
        passed = score >= 70
        failed_items = [item for item in checks if not item["passed"]]
        return {
            "passed": passed,
            "score": score,
            "checks": checks,
            "failed_checks": [item["name"] for item in failed_items],
            "repair_hint": (
                "請補上程式碼證據、完成度與下一步，並改用白話。"
                if failed_items
                else "品質檢查通過。"
            ),
        }

    def build_repair_request(self, *, original_request: str, quality_report: dict[str, Any], style_hint: str = "") -> str:
        hint = str(quality_report.get("repair_hint") or "")
        suffix = f"\n{style_hint}" if style_hint else ""
        return (
            f"{original_request}\n"
            f"上一版回覆品質未達標：{hint}\n"
            "請重整為：1) 這是什麼 2) 程式碼證據 3) 完成度 4) 下一步。"
            f"{suffix}"
        )

    def _collect_text(self, payload: dict[str, Any]) -> str:
        chunks: list[str] = []
        for key in ("summary", "user_friendly_summary", "trace_summary_text", "message"):
            value = payload.get(key)
            if isinstance(value, str):
                chunks.append(value)
        summary_block = payload.get("summary")
        if isinstance(summary_block, dict):
            for value in summary_block.values():
                if isinstance(value, str):
                    chunks.append(value)
        return "\n".join(chunks).strip()
