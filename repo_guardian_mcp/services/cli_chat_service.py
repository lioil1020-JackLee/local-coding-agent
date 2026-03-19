from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from repo_guardian_mcp.services.cli_agent_service import CLIAgentService


@dataclass
class ChatTurnResult:
    ok: bool
    mode: str
    message: str
    payload: dict[str, Any] = field(default_factory=dict)


class CLIChatService:
    def __init__(self, agent_service: CLIAgentService | None = None) -> None:
        self.agent_service = agent_service or CLIAgentService()

    def help_text(self) -> str:
        return (
            "指令:\n"
            "  /help            顯示說明\n"
            "  /skills          顯示 skill registry v2 metadata\n"
            "  /plan <text>     只做規劃\n"
            "  /run <text>      執行任務\n"
            "  /exit            離開 chat\n"
            "\n"
            "若直接輸入自然語言，預設會走 /plan。"
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

        if text.startswith("/plan "):
            prompt = text[len("/plan "):].strip()
            ctx = self.agent_service.build_context(repo_root=repo_root, user_request=prompt, task_type=default_task_type)
            payload = self.agent_service.create_plan(ctx)
            return ChatTurnResult(ok=bool(payload.get("ok")), mode="plan", message="已建立 plan。", payload=payload)

        if text.startswith("/run "):
            prompt = text[len("/run "):].strip()
            inferred_type = "analyze" if any(token in prompt.lower() for token in ["分析", "analyze", "overview", "scan"]) else default_task_type
            ctx = self.agent_service.build_context(repo_root=repo_root, user_request=prompt, task_type=inferred_type)
            payload = self.agent_service.run(ctx)
            return ChatTurnResult(ok=bool(payload.get("ok")), mode="run", message="已執行任務。", payload=payload)

        inferred_type = "analyze" if any(token in text.lower() for token in ["分析", "analyze", "overview", "scan"]) else default_task_type
        ctx = self.agent_service.build_context(repo_root=repo_root, user_request=text, task_type=inferred_type)
        payload = self.agent_service.create_plan(ctx)
        return ChatTurnResult(ok=bool(payload.get("ok")), mode="plan", message="已建立 plan。", payload=payload)
