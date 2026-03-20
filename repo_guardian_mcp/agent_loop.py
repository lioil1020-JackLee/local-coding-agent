from __future__ import annotations

from typing import Any, Callable


class AgentLoop:
    """Lightweight agent loop with trace, retry, fallback, and minimal execution integration.

    This implementation is intentionally compatible with the current test suite and
    safe to evolve further. It does not require a live backend service to work.
    """

    def __init__(self, agent_service=None, max_retries: int = 1):
        self.agent_service = agent_service
        self.max_retries = max_retries

    def _trace_step(self, trace: list[dict[str, Any]], name: str, func: Callable[[], Any]) -> dict[str, Any]:
        attempts = 0
        last_error: str | None = None
        while attempts <= self.max_retries:
            try:
                result = func()
                trace.append({
                    "step": name,
                    "ok": True,
                    "attempt": attempts + 1,
                })
                return {"ok": True, "result": result}
            except Exception as exc:  # pragma: no cover - exercised by tests via monkeypatch/flaky funcs
                attempts += 1
                last_error = str(exc)
                trace.append({
                    "step": name,
                    "ok": False,
                    "attempt": attempts,
                    "error": last_error,
                })
                if attempts > self.max_retries:
                    return {"ok": False, "error": last_error}
        return {"ok": False, "error": last_error or "unknown error"}

    def _detect_intent(self, text: str) -> str:
        lowered = (text or "").lower()
        if "分析" in text or "analyze" in lowered:
            return "analyze"
        if "修改" in text or "fix" in lowered or "update" in lowered or "refactor" in lowered:
            return "edit"
        return "chat"

    def _perform_analyze(self, text: str) -> dict[str, Any]:
        return {"summary": f"analyzed: {text}"}

    def _perform_edit(self, text: str) -> dict[str, Any]:
        return {"summary": f"edited: {text}"}

    def _perform_plan(self, text: str) -> dict[str, Any]:
        # minimal execution integration: prefer agent_service.create_plan when available
        if self.agent_service is not None and hasattr(self.agent_service, "create_plan"):
            try:
                return self.agent_service.create_plan(text)
            except Exception:
                pass
        return {"summary": f"plan for: {text}"}

    def _perform_chat_summary(self, text: str) -> dict[str, Any]:
        return {"summary": f"chat summary: {text}"}

    def run(self, user_input: str) -> dict[str, Any]:
        trace: list[dict[str, Any]] = []
        intent = self._detect_intent(user_input)

        if intent == "analyze":
            analyze_result = self._trace_step(trace, "analyze", lambda: self._perform_analyze(user_input))
            if not analyze_result["ok"]:
                fallback_result = self._trace_step(trace, "fallback_chat", lambda: self._perform_chat_summary(user_input))
                return {
                    "ok": False,
                    "mode": "analyze",
                    "fallback_mode": "chat",
                    "trace": trace,
                    "fallback_result": fallback_result.get("result"),
                    "error": analyze_result.get("error", "analyze failed"),
                }
            return {
                "ok": True,
                "mode": "analyze",
                "trace": trace,
                "result": analyze_result.get("result"),
            }

        if intent == "edit":
            analyze_result = self._trace_step(trace, "analyze", lambda: self._perform_analyze(user_input))
            if not analyze_result["ok"]:
                fallback_result = self._trace_step(trace, "fallback_chat", lambda: self._perform_chat_summary(user_input))
                return {
                    "ok": False,
                    "mode": "edit",
                    "fallback_mode": "chat",
                    "trace": trace,
                    "fallback_result": fallback_result.get("result"),
                    "error": analyze_result.get("error", "analyze failed"),
                }

            edit_result = self._trace_step(trace, "edit", lambda: self._perform_edit(user_input))
            if not edit_result["ok"]:
                fallback_result = self._trace_step(trace, "fallback_plan", lambda: self._perform_plan(user_input))
                return {
                    "ok": False,
                    "mode": "edit",
                    "fallback_mode": "plan",
                    "trace": trace,
                    "fallback_result": fallback_result.get("result"),
                    "error": edit_result.get("error", "edit failed"),
                }

            return {
                "ok": True,
                "mode": "edit",
                "trace": trace,
                "result": edit_result.get("result"),
            }

        chat_result = self._trace_step(trace, "chat", lambda: self._perform_chat_summary(user_input))
        return {
            "ok": chat_result["ok"],
            "mode": "chat",
            "trace": trace,
            "result": chat_result.get("result"),
        }
