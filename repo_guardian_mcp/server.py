from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from repo_guardian_mcp.settings import Settings
from repo_guardian_mcp.tools.find_entrypoints import find_entrypoints
from repo_guardian_mcp.tools.impact_analysis import impact_analysis
from repo_guardian_mcp.tools.preview_diff import preview_diff
from repo_guardian_mcp.tools.propose_patch import propose_patch
from repo_guardian_mcp.tools.read_code_region import read_code_region
from repo_guardian_mcp.tools.repo_overview import repo_overview
from repo_guardian_mcp.tools.search_code import search_code
from repo_guardian_mcp.tools.stage_patch import stage_patch
from repo_guardian_mcp.tools.symbol_index import symbol_index


settings = Settings.load()
mcp = FastMCP("repo-guardian")


@mcp.tool()
def get_repo_overview() -> dict:
    """取得目前 repo 的總覽資訊。"""
    result = repo_overview(settings.workspace_root)
    return result.model_dump()


@mcp.tool()
def get_entrypoints() -> dict:
    """取得目前 repo 的可能入口點。"""
    result = find_entrypoints(settings.workspace_root)
    return {"entrypoints": result}


@mcp.tool()
def search_codebase(query: str) -> dict:
    """在目前 repo 中搜尋關鍵字。"""
    result = search_code(settings.workspace_root, query)
    return {"results": result}


@mcp.tool()
def get_code_region(file_path: str, start_line: int, end_line: int) -> dict:
    """讀取 repo 中指定檔案的程式碼區段。"""
    return read_code_region(
        settings.workspace_root,
        file_path,
        start_line,
        end_line,
    )


@mcp.tool()
def get_symbol_index() -> dict:
    """建立目前 repo 的 Python symbol 索引。"""
    result = symbol_index(settings.workspace_root)
    return {"symbols": result}


@mcp.tool()
def get_impact_analysis(symbol_name: str) -> dict:
    """分析指定 symbol 在目前 repo 中的影響範圍。"""
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
    """根據任務與上下文產生結構化 patch proposal。"""
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
    """預覽結構化 patch proposal 產生的 unified diff。"""
    return preview_diff(
        patch=patch,
        repo_root=str(settings.workspace_root),
    )


@mcp.tool()
def stage_patch_tool(patch: dict) -> dict:
    """將結構化 patch proposal 套用到 workspace。"""
    return stage_patch(
        patch=patch,
        repo_root=str(settings.workspace_root),
    )


def main() -> None:
    """啟動 MCP 伺服器。"""
    print(f"repo-guardian MCP server starting... workspace={settings.workspace_root}")
    mcp.run()


if __name__ == "__main__":
    main()