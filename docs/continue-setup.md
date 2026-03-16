# Continue Setup

本文件說明如何將 **Continue.dev** 與 local-coding-agent MCP server
整合。

Continue 是一個 VS Code / JetBrains 的 AI coding assistant，可以呼叫本地
MCP tools。

------------------------------------------------------------------------

# 安裝 Continue

VS Code:

1.  開啟 Extensions
2.  搜尋 Continue
3.  安裝

JetBrains:

1.  開啟 Plugins
2.  搜尋 Continue
3.  安裝

------------------------------------------------------------------------

# MCP Server 啟動

在專案目錄執行：

python -m repo_guardian_mcp.server

如果成功，會看到：

repo-guardian MCP server starting... workspace=`<path>`{=html}

------------------------------------------------------------------------

# Continue config

在 Continue 設定 MCP server：

config.yaml

範例：

mcpServers:

repo-guardian: command: python args: - -m - repo_guardian_mcp.server

------------------------------------------------------------------------

# 可用 tools

Continue 會自動發現 MCP tools，例如：

run_task_pipeline get_session_status repo_overview search_codebase
preview_diff

------------------------------------------------------------------------

# Example workflow

在 Continue 中你可以要求：

"修改 README.md 並新增一行"

Agent 會：

create_task_session\
run_task_pipeline\
preview diff\
validation

------------------------------------------------------------------------

# 注意事項

建議：

-   sandbox 修改
-   不直接修改主 repo
-   使用 diff preview
