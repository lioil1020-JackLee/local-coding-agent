# Changelog

本文件記錄 **local-coding-agent / repo_guardian MCP server** 的重要版本變更。

本專案目前採用：

- `v1.0.0` 作為第一個正式可用版本
- 後續版本依功能演進持續追加

---

# [v1.0.1-dev] - 2026-03-16

## Changed

### Continue / MCP 整合現況補充

- 已確認 `repo_guardian` MCP server 可由 Continue 成功連線並呼叫分析類工具
- 已確認可正常呼叫：
  - `get_repo_overview`
  - `get_entrypoints`
  - `get_symbol_index`
  - `analyze_repo_tool`
- 已確認 Continue 在分析任務中，能以 MCP tool 為主完成 repo 導覽流程

### Continue Prompt / Agent 行為調整

- `qwen25-main` 補強：
  - 當使用者要求「分析這個專案 / 看懂這個專案 / 分析整個專案架構」時，應優先使用 `analyze_repo_tool`
- `qwen25-builder` 補強：
  - 當使用者要求列出工具流程時，只輸出 MCP tool 流程，不輸出額外的「需求理解 / 修改計畫 / 風險」模板
  - 當使用者要求只產生 patch proposal / diff 時，禁止退回 Continue 內建直接編輯流程
  - 當任務涉及 repository 修改時，優先走 `repo_guardian` MCP 安全流程

### Safety / Prompting Notes

- 補充 builder agent 的安全限制：
  - 先分析再修改
  - 不得自行發明不存在的 tool
  - 不得在未明確要求下直接 patch
  - 不得修改 `repo_guardian_mcp/tools/` 內的 MCP 工具實作，除非使用者明確要求

## Fixed

### Git Utility Cleanup

- 整理 `repo_guardian_mcp/utils/git_utils.py`
- 移除重複的 `get_diff_against_commit` 定義
- 統一 git 指令執行與 timeout 行為
- 保持 `run_task_pipeline` 測試通過

### Pipeline Contract Consistency

- 恢復 `TaskOrchestrator.run()` 回傳中的 `diff_text`
- 使既有 pytest 測試與 pipeline contract 保持一致

## Verified

### Test Status

- 已確認 `uv run pytest` 通過
- 目前測試數量：`10 passed`

### MCP / Agent Status

- 已確認：
  - Continue 可連線到 `repo_guardian` MCP server
  - 分析任務可成功呼叫 MCP tool
  - `run_task_pipeline` 在 terminal 直接執行時可正常完成 sandbox session、diff preview、validation 流程

## Notes

### 目前狀態定位

目前專案可視為：

**repo_guardian v1 已穩定可用，並已完成 Continue + MCP 的基礎串接。**

目前已具備：

- sandbox isolation
- structured edit
- diff preview
- validation hook
- session tracking
- MCP integration
- Continue analysis flow
- test coverage

### 已知限制

目前仍有以下限制：

- `run_task_pipeline_tool` 在 Continue 中可能出現 tool timeout 或 agent 行為不穩定
- `qwen25-builder` 在部分情況下仍可能偏向自行產生編輯內容，而非完全遵守 repo_guardian patch flow
- patch proposal 對文字錨點與上下文品質較敏感，對 README 類檔案的 append 任務仍需更穩定的提示策略

### 下一步方向

下一步建議優先投入：

1. 強化 builder 對 repo_guardian MCP tools 的使用穩定性
2. 讓 agent 形成固定的「先 search → 再 read → 再 propose_patch → 再 preview_diff」流程
3. 規劃高階 orchestrator / planning loop，使使用者只需輸入白話需求即可自動選擇工具
4. 補上更完整的 validation / apply / rollback 流程設計
5. 持續改善 Continue prompt，使分析任務與修改任務分流更穩定

---

# [v1.0.0] - 2026-03-16

## Added

### MCP Server 基礎能力

- 建立 `repo_guardian_mcp.server` 作為 MCP server 入口
- 建立 `tool_registry.py` 作為 tool 註冊中心
- 可透過 MCP 暴露 repo tools 與 sandbox workflow tools

### Repository Analysis Tools

- `repo_overview`
- `find_entrypoints`
- `search_code`
- `read_code_region`
- `impact_analysis`
- `plan_change`
- `preview_diff`
- `propose_patch`
- `stage_patch`

### Sandbox Session Workflow

- `create_task_session`
- `preview_session_diff`
- `run_task_pipeline`
- `get_session_status`
- `apply_to_workspace`
- `cleanup_sandbox`

### Structured Editing

- 支援 `append` 模式
- 支援 `replace` 模式
- 支援 `operations[]` 多步操作
- 可在 sandbox worktree 中進行結構化文字修改

### Session Metadata

- session metadata 寫入：
  - `status`
  - `edited_files`
  - `changed`
  - `summary`
  - `validation`
- 支援 `get_session_status(session_id)` 查詢 session 狀態

### Validation Hook

- 建立 v1 最小 validation hook
- 規則：
  - diff 存在 → pass
  - diff 不存在 → fail

### Runtime Layout

- 建立：
  - `agent_runtime/sandbox_worktrees/`
  - `agent_runtime/sessions/`
  - `agent_runtime/logs/`
  - `agent_runtime/snapshots/`

### Tests

- 新增 pytest 測試
- 已覆蓋：
  - `run_task_pipeline`
  - `get_session_status`
  - `repo_overview`
  - `patch_service`
  - `validation_service`
  - `text_guard`

### Documentation

- 新增與整理：
  - `README.md`
  - `docs/architecture.md`
  - `docs/workflow.md`
  - `docs/validation-policy.md`
  - `docs/tool-contracts.md`
  - `docs/continue-setup.md`
  - `docs/system-diagram.md`
  - `docs/目錄結構.md`

## Notes

### v1 定位

`v1.0.0` 為 **最小可運作的 local coding agent framework**。

目前已具備：

- sandbox isolation
- structured edit
- diff preview
- validation hook
- session tracking
- MCP integration
- test coverage

### v2 方向

未來版本可能加入：

- 真正的 test / lint / typecheck validation
- semantic patch generation
- impact-aware planning
- patch review workflow
- multi-file refactor pipeline
- planner / reviewer / summarizer agent integration
