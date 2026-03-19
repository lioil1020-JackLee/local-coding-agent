from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class AgentSessionState:
    session_id: str
    repo_root: str
    status: str = "active"
    goal: str | None = None
    active_mode: str = "chat"
    selected_skill: str | None = None
    last_user_request: str | None = None
    current_plan: dict[str, Any] | None = None
    last_analysis: dict[str, Any] | None = None
    last_execution: dict[str, Any] | None = None
    last_structured_context: dict[str, Any] | None = None
    working_session_id: str | None = None
    pending_action: str | None = None
    artifacts: dict[str, Any] = field(default_factory=dict)
    trace: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class AgentSessionStateService:
    def __init__(self, repo_root: str | Path) -> None:
        self.repo_root = str(Path(repo_root).resolve())
        self.sessions_dir = Path(self.repo_root) / "agent_runtime" / "agent_sessions"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

    def _session_file(self, session_id: str) -> Path:
        return self.sessions_dir / f"{session_id}.json"

    def new_session_id(self) -> str:
        return f"agent-{uuid.uuid4().hex[:12]}"

    def create(self, *, active_mode: str = "chat", goal: str | None = None) -> AgentSessionState:
        state = AgentSessionState(
            session_id=self.new_session_id(),
            repo_root=self.repo_root,
            active_mode=active_mode,
            goal=goal,
        )
        self.save(state)
        return state

    def load(self, session_id: str) -> AgentSessionState:
        data = json.loads(self._session_file(session_id).read_text(encoding="utf-8"))
        return AgentSessionState(**data)

    def save(self, state: AgentSessionState) -> None:
        self._session_file(state.session_id).write_text(
            json.dumps(state.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def get_or_create(self, session_id: str | None, *, active_mode: str = "chat") -> AgentSessionState:
        if session_id:
            try:
                return self.load(session_id)
            except FileNotFoundError:
                pass
        return self.create(active_mode=active_mode)
