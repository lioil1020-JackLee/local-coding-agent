# local-coding-agent

本專案是一個 **本地 Coding Agent / Repo Guardian MCP Server
的實驗框架**。

目標是建立一個安全的程式碼修改流程（coding pipeline），透過 sandbox
worktree、結構化 edit 與 MCP server，讓 agent 能安全地修改 repository。

------------------------------------------------------------------------

# 專案狀態

目前版本：

repo_guardian coding agent **v1**

已完成最小可運作版本（Minimum Viable Coding Agent）。

------------------------------------------------------------------------

# 核心流程

create_task_session ↓ sandbox edit ↓ preview diff ↓ validation hook ↓
update session metadata ↓ query session status

------------------------------------------------------------------------

# 核心功能

目前 v1 支援：

-   sandbox session
-   structured edit
-   multi operations
-   diff preview
-   validation hook
-   session metadata
-   MCP tool integration
-   pytest tests

------------------------------------------------------------------------

# 專案結構（簡化版）

``` text
local-coding-agent
│
├─ repo_guardian_mcp/      MCP server + coding agent
│  ├─ tools/               MCP tools
│  ├─ services/            核心邏輯
│  └─ utils/               共用工具
│
├─ agent_runtime/          agent 執行資料
│  ├─ sandbox_worktrees/
│  ├─ sessions/
│  └─ logs/
│
├─ docs/                   系統文件
│  ├─ architecture.md
│  ├─ workflow.md
│  ├─ validation-policy.md
│  └─ tool-contracts.md
│
└─ tests/                  pytest 測試
```

完整結構請參考：

docs/目錄結構.md

------------------------------------------------------------------------

# MCP Server

啟動 server：

python -m repo_guardian_mcp.server

------------------------------------------------------------------------

# 測試

執行全部測試：

uv run pytest

------------------------------------------------------------------------

# 未來規劃（v2）

未來可能加入：

-   semantic patch generation
-   impact analysis
-   lint / test validation
-   automated refactor
-   planning agent




