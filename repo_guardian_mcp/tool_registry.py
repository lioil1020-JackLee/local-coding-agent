from __future__ import annotations

from importlib import import_module
from typing import Callable

TOOLS: dict[str, str] = {}


def register(name: str, target: str) -> None:
    TOOLS[name] = target


def get_tool(name: str) -> Callable:
    if name not in TOOLS:
        raise KeyError(f"Tool not found: {name}")
    module_path, func_name = TOOLS[name].split(":")
    module = import_module(module_path)
    return getattr(module, func_name)


def list_tools() -> list[str]:
    return sorted(TOOLS.keys())


register("analyze_repo", "repo_guardian_mcp.tools.analyze_repo:analyze_repo")
register("find_entrypoints", "repo_guardian_mcp.tools.find_entrypoints:find_entrypoints")
register("get_session_status", "repo_guardian_mcp.tools.get_session_status:get_session_status")

register("create_task_session", "repo_guardian_mcp.tools.create_task_session:create_task_session")
register("preview_session_diff", "repo_guardian_mcp.tools.preview_session_diff:preview_session_diff")
register("run_validation_pipeline", "repo_guardian_mcp.tools.run_validation_pipeline:run_validation_pipeline")
register("rollback_session", "repo_guardian_mcp.tools.rollback_session:rollback_session")
register("run_task_pipeline", "repo_guardian_mcp.tools.run_task_pipeline:run_task_pipeline")

register("search_codebase", "repo_guardian_mcp.tools.search_code:search_code")
register("get_code_region", "repo_guardian_mcp.tools.read_code_region:read_code_region")
register("get_repo_overview", "repo_guardian_mcp.tools.repo_overview:repo_overview")

register("propose_patch", "repo_guardian_mcp.tools.propose_patch:propose_patch")
register("preview_diff", "repo_guardian_mcp.tools.preview_diff:preview_diff")
register("stage_patch", "repo_guardian_mcp.tools.stage_patch:stage_patch")

register("move_file", "repo_guardian_mcp.tools.move_file:move_file")
register("cleanup_sandbox", "repo_guardian_mcp.tools.cleanup_sandbox:cleanup_sandbox")
register("cleanup_sessions", "repo_guardian_mcp.tools.cleanup_sessions:cleanup_sessions_tool")
register("list_sessions", "repo_guardian_mcp.tools.list_sessions:list_sessions_tool")
register("pin_session", "repo_guardian_mcp.tools.pin_session:pin_session_tool")
register("resume_session", "repo_guardian_mcp.tools.resume_session:resume_session_tool")
