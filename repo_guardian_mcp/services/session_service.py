from __future__ import annotations

"""
session_service 提供建立與載入 task session 的能力。

每個 session 存儲為 JSON 檔案，包含沙盒路徑、版本資訊等。
"""

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path

from repo_guardian_mcp.models import TaskSession


class SessionService:
    def __init__(self, sessions_dir: str | Path) -> None:
        self.sessions_dir = Path(sessions_dir)
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

    def _session_file(self, session_id: str) -> Path:
        return self.sessions_dir / f"{session_id}.json"

    def new_session_id(self) -> str:
        # 使用前 12 個 hex 作為簡短 id
        return uuid.uuid4().hex[:12]

    def build_session(
        self,
        session_id: str,
        repo_root: str | Path,
        sandbox_path: str | Path,
        branch_name: str,
        base_branch: str,
        base_commit: str,
    ) -> TaskSession:
        return TaskSession(
            session_id=session_id,
            repo_root=str(Path(repo_root).resolve()),
            sandbox_path=str(Path(sandbox_path).resolve()),
            branch_name=branch_name,
            base_branch=base_branch,
            base_commit=base_commit,
            created_at=datetime.now(UTC),
            status="active",
        )

    def save_session(self, session: TaskSession) -> None:
        self._session_file(session.session_id).write_text(
            session.model_dump_json(indent=2),
            encoding="utf-8",
        )

    def load_session(self, session_id: str) -> TaskSession:
        path = self._session_file(session_id)
        data = json.loads(path.read_text(encoding="utf-8"))
        return TaskSession.model_validate(data)