from __future__ import annotations

from typing import Any

from repo_guardian_mcp.services.cli_agent_service import CLIAgentService
from repo_guardian_mcp.services.edit_execution_orchestrator import EditExecutionOrchestrator


class ExecutionFlowOrchestrator:
    """Execution-only layer: receives resolved task intent and performs execution."""

    def __init__(
        self,
        *,
        agent_service: CLIAgentService | None = None,
        edit_orchestrator: EditExecutionOrchestrator | None = None,
    ) -> None:
        self._agent_service = agent_service or CLIAgentService()
        self._edit_orchestrator = edit_orchestrator or EditExecutionOrchestrator()

    def execute_agent(self, *, repo_root: str, user_request: str, task_type: str, session_id: str | None, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        ctx = self._agent_service.build_context(
            repo_root=repo_root,
            user_request=user_request,
            task_type=task_type,
            session_id=session_id,
            metadata=dict(metadata or {}),
        )
        return self._agent_service.run(ctx)

    def execute_analyze(self, *, repo_root: str, user_request: str = "", metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        ctx = self._agent_service.build_context(
            repo_root=repo_root,
            user_request=user_request or "analyze repository",
            task_type="analyze",
            metadata=dict(metadata or {}),
        )
        return self._agent_service.run(ctx)

    def execute_edit(
        self,
        *,
        repo_root: str,
        relative_path: str,
        content: str,
        mode: str,
        old_text: str | None,
        operations: list[dict[str, Any]] | None,
        read_only: bool = False,
    ) -> dict[str, Any]:
        return self._edit_orchestrator.run(
            repo_root=repo_root,
            relative_path=relative_path,
            content=content,
            mode=mode,
            old_text=old_text,
            operations=operations,
            read_only=read_only,
        )
