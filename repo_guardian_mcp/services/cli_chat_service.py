from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import os

from repo_guardian_mcp.services.agent_session_runtime import AgentSessionRuntime
from repo_guardian_mcp.services.agent_session_state_service import AgentSessionStateService
from repo_guardian_mcp.services.cli_agent_service import CLIAgentService
from repo_guardian_mcp.services.rollback_service import rollback_session
from repo_guardian_mcp.tools.list_sessions import list_sessions_tool
from repo_guardian_mcp.tools.preview_session_diff import preview_session_diff
from repo_guardian_mcp.tools.resume_session import resume_session_tool


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
            "  /help                     顯示說明\n"
            "  /skills                   顯示 skill registry v3 metadata\n"
            "  /plan <text>              只做規劃，保留在 agent session\n"
            "  /run <text>               立刻執行任務\n"
            "  /apply                    套用上一輪待執行 plan\n"
            "  /status                   顯示目前 agent session 狀態\n"
            "  /session list             列出 task sessions\n"
            "  /session resume <id>      恢復 session 並設成目前 working session\n"
            "  /diff [session_id]        顯示目前或指定 working session diff\n"
            "  /rollback [session_id]    回滾目前或指定 working session\n"
            "  /exit                     離開 chat\n"
            "\n"
            "若直接輸入自然語言，會優先走 session-aware routing。"
        )

    def _resolve_sessions_dir(self, repo_root: str) -> str:
        return str((Path(repo_root).resolve() / "agent_runtime" / "sessions").resolve())

    def _load_agent_state(self, repo_root: str):
        if not self._agent_session_id:
            return None
        try:
            return AgentSessionStateService(repo_root).load(self._agent_session_id)
        except FileNotFoundError:
            return None

    def _get_or_create_agent_state(self, repo_root: str):
        service = AgentSessionStateService(repo_root)
        state = service.get_or_create(self._agent_session_id, active_mode="chat")
        self._agent_session_id = state.session_id
        return state, service

    def _command_session_list(self, repo_root: str) -> ChatTurnResult:
        result = list_sessions_tool(self._resolve_sessions_dir(repo_root))
        return ChatTurnResult(bool(result.get("ok")), "session_list", "已列出 task sessions。", payload=result)

    def _command_session_resume(self, repo_root: str, session_id: str) -> ChatTurnResult:
        result = resume_session_tool(self._resolve_sessions_dir(repo_root), session_id=session_id)
        ok = bool(result.get("ok"))
        payload = dict(result)

        if ok:
            state, state_service = self._get_or_create_agent_state(repo_root)
            state.working_session_id = session_id
            state.pending_action = None
            state.trace.append({"event": "bind_working_session", "session_id": session_id})
            state_service.save(state)
            payload["agent_session_id"] = state.session_id
            payload["working_session_id"] = session_id
            return ChatTurnResult(True, "session_resume", "已恢復並綁定 working session。", payload=payload)

        payload.setdefault("agent_session_id", self._agent_session_id)
        return ChatTurnResult(False, "session_resume", "session 恢復失敗。", payload=payload)

    def _command_diff(self, repo_root: str, session_id: str | None) -> ChatTurnResult:
        target_session = session_id
        if not target_session:
            state = self._load_agent_state(repo_root)
            target_session = state.working_session_id if state else None
        if not target_session:
            return ChatTurnResult(False, "diff", "目前沒有可預覽的 working session diff。")

        previous = Path.cwd()
        try:
            os.chdir(repo_root)
            result = preview_session_diff(target_session)
        finally:
            os.chdir(previous)

        payload = dict(result)
        payload.setdefault("agent_session_id", self._agent_session_id)
        payload.setdefault("working_session_id", target_session)
        return ChatTurnResult(
            bool(result.get("ok")),
            "diff",
            "已載入 working session diff。" if result.get("ok") else "載入 diff 失敗。",
            payload=payload,
        )

    def _command_rollback(self, repo_root: str, session_id: str | None) -> ChatTurnResult:
        target_session = session_id
        state = self._load_agent_state(repo_root)
        if not target_session and state is not None:
            target_session = state.working_session_id
        if not target_session:
            return ChatTurnResult(False, "rollback", "目前沒有可回滾的 working session。")

        result = rollback_session(repo_root=repo_root, session_id=target_session, cleanup_workspace=True)

        if result.get("ok") and state is not None and state.working_session_id == target_session:
            state.working_session_id = None
            state.pending_action = None
            state.last_execution = result
            state.trace.append({"event": "clear_working_session", "session_id": target_session})
            AgentSessionStateService(repo_root).save(state)

        payload = dict(result)
        payload.setdefault("agent_session_id", self._agent_session_id)
        payload.setdefault("working_session_id", target_session)
        return ChatTurnResult(
            bool(result.get("ok")),
            "rollback",
            "已回滾指定 session。" if result.get("ok") else "回滾失敗。",
            payload=payload,
        )

    def _render_trace(self, trace: list[dict[str, Any]]) -> str:
        lines = ["[agent trace]"]
        for step in trace:
            status = "✅" if step.get("ok", True) else "❌"
            step_name = step.get("step") or step.get("event") or "unknown"
            lines.append(f"- {step_name} {status}")
        return "\n".join(lines)

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

        if text == "/session list":
            return self._command_session_list(repo_root)

        if text.startswith("/session resume "):
            session_id = text[len("/session resume "):].strip()
            if not session_id:
                return ChatTurnResult(False, "session_resume", "請提供 session_id。")
            return self._command_session_resume(repo_root, session_id)

        if text == "/diff" or text.startswith("/diff "):
            session_id = text[len("/diff "):].strip() if text.startswith("/diff ") else None
            return self._command_diff(repo_root, session_id or None)

        if text == "/rollback" or text.startswith("/rollback "):
            session_id = text[len("/rollback "):].strip() if text.startswith("/rollback ") else None
            return self._command_rollback(repo_root, session_id or None)

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
