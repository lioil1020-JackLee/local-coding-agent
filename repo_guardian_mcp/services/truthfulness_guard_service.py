from __future__ import annotations

from typing import Any


class TruthfulnessGuardService:
    """降低不實陳述風險，並強制在困難情境提供替代方案。"""

    _CONFIDENT_WORDS = ("一定", "完全", "已完成", "沒問題", "保證")

    def evaluate(self, *, user_request: str, payload: dict[str, Any] | None) -> dict[str, Any]:
        payload = dict(payload or {})
        ok = bool(payload.get("ok"))
        checks: list[dict[str, Any]] = []

        evidence = self._has_evidence(payload)
        checks.append(
            {
                "name": "has_evidence",
                "passed": evidence or (not ok),
                "message": "有可驗證證據。" if (evidence or (not ok)) else "缺少可驗證證據。",
            }
        )

        summary_text = self._collect_text(payload)
        has_confident = any(word in summary_text for word in self._CONFIDENT_WORDS)
        checks.append(
            {
                "name": "no_false_confidence",
                "passed": not (has_confident and not ok),
                "message": "未出現不當自信語句。" if not (has_confident and not ok) else "失敗狀態卻出現過度肯定語句。",
            }
        )

        alternatives = self._extract_next_actions(payload)
        need_alternative = (not ok) or (not evidence)
        checks.append(
            {
                "name": "has_alternative_plan",
                "passed": (not need_alternative) or len(alternatives) > 0,
                "message": "有替代方案。" if ((not need_alternative) or len(alternatives) > 0) else "缺少替代方案。",
            }
        )

        score = 100 - sum(35 for item in checks if not item["passed"])
        score = max(0, min(100, score))
        passed = score >= 70
        return {
            "passed": passed,
            "score": score,
            "checks": checks,
            "failed_checks": [item["name"] for item in checks if not item["passed"]],
            "requires_disclosure": (not ok) or (not evidence),
            "summary": (
                "真實性檢查通過。"
                if passed
                else "真實性檢查未通過，需補上誠實說明與替代方案。"
            ),
        }

    def enforce(self, *, user_request: str, payload: dict[str, Any] | None) -> dict[str, Any]:
        output = dict(payload or {})
        report = self.evaluate(user_request=user_request, payload=output)
        output["truthfulness_review"] = report
        if report["passed"]:
            return output

        fallback_actions = self.build_alternative_actions(user_request=user_request, payload=output)
        existing = self._extract_next_actions(output)
        merged = list(dict.fromkeys([*existing, *fallback_actions]))
        output["next_actions"] = merged
        output.setdefault(
            "truthful_disclosure",
            "目前無法保證結果完全正確；我已誠實標記限制，並提供可執行替代方案。",
        )
        return output

    def build_alternative_actions(self, *, user_request: str, payload: dict[str, Any] | None) -> list[str]:
        payload = dict(payload or {})
        actions: list[str] = []
        if payload.get("pipeline_id"):
            actions.append(f"用同一個 pipeline_id={payload['pipeline_id']} 續跑（resume=true）。")
        actions.append("先縮小範圍（例如先看單一模組或單一檔案）再繼續。")
        actions.append("先輸出目前已確認事實與未確認點，再決定下一步。")
        if "完成度" in (user_request or ""):
            actions.append("若要完成度更準，先跑 read_all_python=true 的完整掃描。")
        return actions

    def _has_evidence(self, payload: dict[str, Any]) -> bool:
        return bool(
            payload.get("python_evidence")
            or payload.get("completion_estimate")
            or payload.get("entrypoints")
            or payload.get("step_results")
            or payload.get("standardized_trace")
            or payload.get("trace_summary")
        )

    def _extract_next_actions(self, payload: dict[str, Any]) -> list[str]:
        value = payload.get("next_actions")
        if not isinstance(value, list):
            return []
        return [str(item) for item in value if str(item).strip()]

    def _collect_text(self, payload: dict[str, Any]) -> str:
        chunks: list[str] = []
        for key in ("summary", "message", "user_friendly_summary", "truthful_disclosure"):
            value = payload.get(key)
            if isinstance(value, str):
                chunks.append(value)
        return "\n".join(chunks)
