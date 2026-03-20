from __future__ import annotations
from typing import Any, Dict, List
from repo_guardian_mcp.agent_loop import AgentLoop

class CLIChatService:
    def __init__(self):
        self.loop = AgentLoop()
        self._last_trace: List[Dict[str, Any]] = []

    def _format_trace(self, trace):
        lines = []
        for step in trace:
            status = "OK" if step.get("ok") else "FAIL"
            attempt = step.get("attempt", 1)
            lines.append(f"- {step.get('step')} {status} ({attempt})")
        return "\n".join(lines)

    def handle_input(self, repo_root: str, raw_text: str, default_task_type: str = "auto"):
        text = raw_text.strip()

        if text == "/status":
            return {
                "ok": True,
                "mode": "agent_status",
                "last_trace": self._last_trace,
            }

        result = self.loop.run(text)
        self._last_trace = result.get("trace", [])

        return {
            "ok": result.get("ok", False),
            "mode": result.get("mode"),
            "trace": self._last_trace,
            "trace_text": self._format_trace(self._last_trace),
            "result": result.get("result"),
            "fallback_result": result.get("fallback_result"),
        }