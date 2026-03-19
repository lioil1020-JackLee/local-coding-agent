from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from repo_guardian_mcp.services.agent_session_runtime import AgentSessionRuntime
from repo_guardian_mcp.services.cli_agent_service import CLIAgentService


@dataclass
class ChatTurnResult:
    ok: bool
    mode: str
    message: str
    payload: dict[str, Any] = field(default_factory=dict)


class CLIChatService:
    def __init__(
        self,
        agent_service: CLIAgentService | None = None,
        runtime: AgentSessionRuntime | None = None,
    ) -> None:
        self.agent_service = agent_service or CLIAgentService()
        self.runtime = runtime or AgentSessionRuntime(agent_service=self.agent_service)
        self._agent_session_id: str | None = None

    def help_text(self) -> str:
        return (
            "指令:\n"
            "  /help            顯示說明\n"
            "  /skills          顯示 skill registry v2 metadata\n"
            "  /plan <text>     只做規劃，保留在 agent session\n"
            "  /run <text>      立刻執行任務\n"
            "  /apply           套用上一輪待執行 plan\n"
            "  /status          顯示目前 agent session 狀態\n"
            "  /diff            顯示目前 working session diff\n"
            "  /rollback        回滾目前 working session\n"
            "  /exit            離開 chat\n"
            "\n"
            "若直接輸入自然語言，會優先走 session-aware routing。"
        )

    def handle_input(self, repo_root: str, raw_text: str, default_task_type: str = "auto") -> ChatTurnResult:
        text = (raw_text or "").strip()
        if not text:
            return ChatTurnResult(ok=True, mode="noop", message="請輸入任務，或輸入 /help 查看指令。")

        if text == "/help":
            return ChatTurnResult(ok=True, mode="help", message=self.help_text())

        if text == "/skills":
            payload = {"skills": self.agent_service.skill_registry.list_skill_metadata()}
            return ChatTurnResult(ok=True, mode="skills", message="已列出 skills。", payload=payload)

        if text == "/exit":
            return ChatTurnResult(ok=True, mode="exit", message="已結束 chat。")

        force_plan_only = False
        runtime_text = text
        if text.startswith("/plan "):
            force_plan_only = True
            runtime_text = text[len("/plan "):].strip()
        elif text.startswith("/run "):
            runtime_text = text[len("/run "):].strip()

        result = self.runtime.handle_turn(
            repo_root=repo_root,
            raw_text=runtime_text,
            agent_session_id=self._agent_session_id,
            default_task_type=default_task_type,
            force_plan_only=force_plan_only,
        )
        self._agent_session_id = result.agent_session_id
        payload = dict(result.payload)
        payload.pop("mode", None)
        payload.setdefault("agent_session_id", result.agent_session_id)
        return ChatTurnResult(ok=result.ok, mode=result.mode, message=result.message, payload=payload)
