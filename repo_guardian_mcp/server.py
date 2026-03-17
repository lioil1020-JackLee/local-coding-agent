from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from repo_guardian_mcp.services.conversation_orchestrator import ConversationOrchestrator
from repo_guardian_mcp.services.edit_execution_orchestrator import EditExecutionOrchestrator
from repo_guardian_mcp.settings import Settings
from repo_guardian_mcp.tools.analyze_repo import analyze_repo
from repo_guardian_mcp.tools.create_task_session import create_task_session
from repo_guardian_mcp.tools.find_entrypoints import find_entrypoints
from repo_guardian_mcp.tools.get_session_status import get_session_status
from repo_guardian_mcp.tools.impact_analysis import impact_analysis
from repo_guardian_mcp.tools.preview_diff import preview_diff
from repo_guardian_mcp.tools.preview_session_diff import preview_session_diff
from repo_guardian_mcp.tools.propose_patch import propose_patch
from repo_guardian_mcp.tools.read_code_region import read_code_region
from repo_guardian_mcp.tools.repo_overview import repo_overview
from repo_guardian_mcp.tools.rollback_session import rollback_session
from repo_guardian_mcp.tools.run_task_pipeline import run_task_pipeline
from repo_guardian_mcp.tools.run_validation_pipeline import run_validation_pipeline
from repo_guardian_mcp.tools.search_code import search_code
from repo_guardian_mcp.tools.stage_patch import stage_patch
from repo_guardian_mcp.tools.symbol_index import symbol_index


settings = Settings.load()
mcp = FastMCP("repo_guardian")


def _write_mcp_debug_log(payload: dict) -> None:
    try:
        log_path = Path(settings.workspace_root) / "agent_runtime" / "mcp_debug.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception:
        pass


@mcp.tool()
def handle_user_request_tool(
    user_request: str,
    relative_path: str = "README.md",
    content: str = "pipeline test",
    mode: str = "append",
    old_text: str | None = None,
    operations: list[dict] | None = None,
    session_id: str | None = None,
) -> dict:
    _write_mcp_debug_log(
        {
            "ts": datetime.now().isoformat(),
            "event": "handle_user_request_tool:start",
            "user_request": user_request,
            "relative_path": relative_path,
            "mode": mode,
            "has_operations": bool(operations),
            "session_id": session_id,
        }
    )

    orchestrator = ConversationOrchestrator()
    result = orchestrator.route(
        user_request=user_request,
        repo_root=str(settings.workspace_root),
        relative_path=relative_path,
        content=content,
        mode=mode,
        old_text=old_text,
        operations=operations,
        session_id=session_id,
    )

    _write_mcp_debug_log(
        {
            "ts": datetime.now().isoformat(),
            "event": "handle_user_request_tool:end",
            "ok": isinstance(result, dict) and result.get("ok"),
            "intent": result.get("intent") if isinstance(result, dict) else None,
            "mode": result.get("mode") if isinstance(result, dict) else None,
            "error": result.get("error") if isinstance(result, dict) else "invalid result",
        }
    )

    if not isinstance(result, dict):
        return {
            "ok": False,
            "error": "ConversationOrchestrator.route() 回傳格式錯誤",
        }

    return result


@mcp.tool()
def preview_user_request_plan_tool(
    user_request: str,
    relative_path: str = "README.md",
    content: str = "pipeline test",
    mode: str = "append",
    old_text: str | None = None,
    operations: list[dict] | None = None,
) -> dict:
    orchestrator = ConversationOrchestrator()
    plan = orchestrator.build_plan(
        user_request=user_request,
        repo_root=str(settings.workspace_root),
        relative_path=relative_path,
        content=content,
        mode=mode,
        old_text=old_text,
        operations=operations,
    )

    return {
        "ok": True,
        "intent": plan.intent,
        "mode": plan.mode,
        "summary": plan.summary,
        "steps": [
            {
                "step_type": step.step_type,
                "reason": step.reason,
                "args": step.args,
            }
            for step in plan.steps
        ],
    }


@mcp.tool()
def get_repo_overview() -> dict:
    return repo_overview(settings.workspace_root)


@mcp.tool()
def get_entrypoints() -> dict:
    result = find_entrypoints(settings.workspace_root)
    return {"entrypoints": result}


@mcp.tool()
def search_codebase(query: str) -> dict:
    result = search_code(settings.workspace_root, query)
    return {"results": result}


@mcp.tool()
def get_code_region(file_path: str, start_line: int, end_line: int) -> dict:
    return read_code_region(
        settings.workspace_root,
        file_path,
        start_line,
        end_line,
    )


@mcp.tool()
def get_symbol_index() -> dict:
    result = symbol_index(settings.workspace_root)
    return {"symbols": result}


@mcp.tool()
def get_impact_analysis(symbol_name: str) -> dict:
    return impact_analysis(settings.workspace_root, symbol_name)


@mcp.tool()
def propose_patch_tool(
    task: str,
    relevant_paths: list[str] | None = None,
    readonly_paths: list[str] | None = None,
    context_snippets: list[str] | None = None,
    impact_summary: str | None = None,
    constraints: list[str] | None = None,
    max_files_to_change: int = 5,
    require_tests: bool = True,
    allow_new_files: bool = True,
) -> dict:
    return propose_patch(
        task=task,
        relevant_paths=relevant_paths,
        readonly_paths=readonly_paths,
        context_snippets=context_snippets,
        impact_summary=impact_summary,
        constraints=constraints,
        max_files_to_change=max_files_to_change,
        require_tests=require_tests,
        allow_new_files=allow_new_files,
        repo_root=str(settings.workspace_root),
    )


@mcp.tool()
def preview_diff_tool(patch: dict) -> dict:
    return preview_diff(
        patch=patch,
        repo_root=str(settings.workspace_root),
    )


@mcp.tool()
def stage_patch_tool(patch: dict) -> dict:
    return stage_patch(
        patch=patch,
        repo_root=str(settings.workspace_root),
    )


@mcp.tool()
def create_task_session_tool() -> dict:
    """
    建立正式可編輯 session。

    這裡直接建立 sandbox worktree，
    避免把 workspace 初始化延後到 edit_file_tool，
    否則 Continue 容易在 edit 階段 timeout。
    """
    return create_task_session(
        repo_root=str(settings.workspace_root),
        create_workspace=True,
    )


@mcp.tool()
def edit_file_tool(
    session_id: str,
    relative_path: str = "README.md",
    content: str = "pipeline test",
    mode: str = "append",
    old_text: str | None = None,
) -> dict:
    _write_mcp_debug_log(
        {
            "ts": datetime.now().isoformat(),
            "event": "edit_file_tool:start",
            "session_id": session_id,
            "relative_path": relative_path,
            "mode": mode,
        }
    )

    orchestrator = EditExecutionOrchestrator()
    result = orchestrator.edit_existing_session(
        repo_root=str(settings.workspace_root),
        session_id=session_id,
        relative_path=relative_path,
        content=content,
        mode=mode,
        old_text=old_text,
    )

    _write_mcp_debug_log(
        {
            "ts": datetime.now().isoformat(),
            "event": "edit_file_tool:end",
            "session_id": session_id,
            "ok": isinstance(result, dict) and result.get("ok"),
            "error": result.get("error") if isinstance(result, dict) else "invalid result",
        }
    )

    if not isinstance(result, dict):
        return {
            "ok": False,
            "session_id": session_id,
            "error": "edit_existing_session 回傳格式錯誤",
        }

    diff_preview = result.get("diff_preview", {}) or {}
    validation = result.get("validation", {}) or {}

    return {
        "ok": result.get("ok", False),
        "session_id": result.get("session_id"),
        "changed": result.get("changed"),
        "summary": result.get("summary"),
        "edited_files": result.get("edited_files", []),
        "diff_text": result.get("diff_text", ""),
        "diff_summary": {
            "base_commit": diff_preview.get("base_commit"),
            "changed_files": diff_preview.get("changed_files", []),
        },
        "validation": {
            "passed": validation.get("passed"),
            "reason": validation.get("reason"),
        },
        "error": result.get("error"),
    }


@mcp.tool()
def preview_session_diff_tool(session_id: str) -> dict:
    return preview_session_diff(session_id=session_id)


@mcp.tool()
def get_session_status_tool(session_id: str) -> dict:
    return get_session_status(
        repo_root=str(settings.workspace_root),
        session_id=session_id,
    )


@mcp.tool()
def run_validation_pipeline_tool(session_id: str) -> dict:
    return run_validation_pipeline(
        repo_root=str(settings.workspace_root),
        session_id=session_id,
    )


@mcp.tool()
def rollback_session_tool(session_id: str, cleanup_workspace: bool = True) -> dict:
    return rollback_session(
        repo_root=str(settings.workspace_root),
        session_id=session_id,
        cleanup_workspace=cleanup_workspace,
    )


@mcp.tool()
def analyze_repo_tool() -> dict:
    return analyze_repo(settings.workspace_root)


@mcp.tool()
def run_task_pipeline_tool(
    relative_path: str = "README.md",
    content: str = "pipeline test",
    mode: str = "append",
    old_text: str | None = None,
) -> dict:
    result = run_task_pipeline(
        repo_root=str(settings.workspace_root),
        relative_path=relative_path,
        content=content,
        mode=mode,
        old_text=old_text,
    )

    if not isinstance(result, dict):
        return {
            "ok": False,
            "error": "run_task_pipeline 回傳格式錯誤",
        }

    return result


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
