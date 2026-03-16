# Contributing

歡迎持續改進 **local-coding-agent / repo_guardian MCP server**。

本文件說明此專案的基本開發規則與貢獻方式，也作為後續新對話 / 新 agent session 的交接文件。

---

# 開發目標

本專案的核心方向是：

- 建立安全的 local coding agent framework
- 所有修改預設在 sandbox worktree 中執行
- 所有重要操作都要可追蹤、可檢查、可測試
- 讓 Continue + LM Studio + MCP 的本地體驗，盡量接近 Cursor 類型 agent

---

# 目前實際狀態

目前已確認：

- `repo_guardian` MCP server 可啟動
- Continue 可連線並呼叫分析類 MCP tools
- `qwen25-main` 適合作為分析 / repo 導覽代理
- `qwen25-builder` 適合作為修改 / patch 代理
- `run_task_pipeline` 在 terminal 直接執行可正常完成
- `uv run pytest` 目前通過

目前已知限制：

- `run_task_pipeline_tool` 在 Continue 中可能出現 timeout 或 agent 行為不穩定
- builder 有時會偏向使用內建編輯能力，而不是完全遵守 repo_guardian patch flow
- README / 純文字檔 patch proposal 對上下文與錨點較敏感

---

# 基本原則

## 1. 優先保護主 workspace

所有修改流程應優先使用：

- `create_task_session`
- sandbox worktree
- `preview_session_diff`
- validation hook

不要直接把未經檢查的變更寫入主 repo。

## 2. Tool-first 設計

新增功能時，優先思考：

- 是否應該成為一個 MCP tool
- 是否應該放在 `tools/`
- 是否應該由 `services/` 提供核心邏輯

建議分層：

- `tools/`：輸入輸出、對外介面
- `services/`：核心邏輯
- `utils/`：共用工具函式

## 3. 保持 session traceability

凡是會影響 task workflow 的操作，應考慮是否需要寫回 session metadata，例如：

- `status`
- `edited_files`
- `changed`
- `summary`
- `validation`

## 4. 先做最小可用版，再逐步擴充

建議遵循：

1. 先做最小版本
2. 先讓流程可跑
3. 再補 validation
4. 再補 tests
5. 最後再重構

避免一開始就做太複雜。

---

# Continue / Agent 分工規則

## `qwen25-main`

定位：

- 分析與規劃代理
- 專案導覽
- repo 結構理解
- 找入口點
- 說明模組與流程

適合任務：

- 請分析這個專案
- 先不要改，幫我看懂這個專案
- 入口點在哪
- 幫我找某個流程在哪裡

應優先使用的 MCP tools：

- `analyze_repo_tool`
- `get_repo_overview`
- `get_entrypoints`
- `search_codebase`
- `get_code_region`
- `get_symbol_index`
- `get_impact_analysis`

## `qwen25-builder`

定位：

- 修改與 patch 代理
- 產生 patch proposal
- diff preview
- 後續安全修改流程

適合任務：

- 幫我改
- 幫我實作
- 幫我新增功能
- 產生 patch proposal
- 顯示 diff

應遵守的標準安全流程：

1. `repo_guardian_search_codebase`
2. `repo_guardian_get_code_region`
3. `repo_guardian_propose_patch_tool`
4. `repo_guardian_preview_diff_tool`
5. `repo_guardian_stage_patch_tool`

## builder 額外安全限制

- 先分析再修改，不要直接 patch
- 除非使用者明確要求修改，否則不要產生 patch
- 不得修改 `repo_guardian_mcp/tools/` 內的 MCP 工具實作，除非使用者明確要求
- 不得自行發明不存在的 tool
- 不得把分析內容寫入程式檔案
- 若使用者明確要求「不要直接修改任何檔案」，則不可退回使用 Continue 內建直接編輯方式

---

# 專案結構約定

## 新增 Tool

如果你要新增 MCP tool：

1. 在 `repo_guardian_mcp/tools/` 新增對應檔案
2. 在 `repo_guardian_mcp/server.py` 暴露成 MCP tool
3. 補 pytest 測試
4. 更新 docs 與 CHANGELOG

例如：

- `tools/my_tool.py`
- `@mcp.tool()`

## 新增 Service

如果邏輯會被多個 tool 共用，應放到：

`repo_guardian_mcp/services/`

例如：

- sandbox 編輯
- session 更新
- validation
- report generation

## 新增測試

測試請放在：

`tests/`

命名格式：

`test_<feature>.py`

例如：

- `test_run_task_pipeline.py`
- `test_get_session_status.py`

執行方式：

`uv run pytest`

---

# 程式風格建議

## 小步修改

- 每次只做一小個功能
- 每次修改都應可測試

## 錯誤要可讀

tool 回傳建議包含：

- `ok`
- `error`（失敗時）

## 優先結構化輸出

tool 輸出盡量使用 dict，避免回傳不可解析字串。

## prompt 與 agent 行為

當你在改善 Continue prompt / agent 行為時：

- 盡量只加一小段規則
- 每次調整後要重新開啟 VSCode / Reload Window
- 每次調整後都要重新測試同一條任務
- 避免同時改太多 prompt，否則難以判斷哪段規則有效

---

# 文件更新原則

如果你修改了下列任一項，請同步更新 docs：

- workflow
- tool contract
- validation policy
- project structure
- README
- Continue / MCP 使用規則
- CHANGELOG

建議至少檢查：

- `docs/workflow.md`
- `docs/tool-contracts.md`
- `docs/validation-policy.md`
- `docs/目錄結構.md`
- `CHANGELOG.md`

---

# 建議的開發流程

## MCP / 工具功能開發

建立 / 修改 service  
↓  
建立 / 修改 tool  
↓  
掛到 `server.py`  
↓  
補 pytest  
↓  
更新 docs

## Continue / agent prompt 調整

修改 `config.yaml`  
↓  
Reload Window / 重開 VSCode  
↓  
重新測同一條指令  
↓  
觀察：
- 有沒有用對 MCP tools
- 有沒有亂改檔
- 有沒有退回 Continue 內建編輯
- 結果是否比前一版穩定

---

# 建議的任務驗證順序

若要驗證 agent 是否真的變穩定，建議照這個順序測：

1. 分析任務  
   - 例如：`請分析這個專案`

2. 單一工具流程列舉  
   - 例如：`如果要修改 README.md，列出最小必要工具流程`

3. 純分析 patch 任務  
   - 例如：`請使用 repo_guardian MCP tools 產生 patch proposal 並顯示 diff，不要 stage patch`

4. 真正修改流程  
   - 例如：`明確要求修改、預覽 diff、再人工確認是否套用`

---

# Commit 建議

可使用簡單前綴：

- `feat:` 新功能
- `fix:` 修正問題
- `refactor:` 重構
- `docs:` 文件更新
- `test:` 測試更新

例如：

- `feat: add analyze_repo_tool`
- `docs: update continue agent workflow`
- `fix: clean up git_utils duplicate diff helper`
- `test: keep run_task_pipeline contract stable`

---

# Release 建議

當功能達到穩定狀態時：

1. 更新 `CHANGELOG.md`
2. 更新 `README.md`
3. 確認 `uv run pytest` 通過
4. 建立 release tag

例如：

- `v1.0.0`

若只是持續調整 Continue / MCP prompt 行為，可先記錄為：

- `v1.0.1-dev`

---

# 新對話交接建議

若要在新對話延續這個專案，建議先提供：

1. `CHANGELOG.md`
2. `CONTRIBUTING.md`
3. 目前 `config.yaml`
4. `repo_guardian_mcp/server.py`
5. `repo_guardian_mcp/services/task_orchestrator.py`

並在新對話第一句說明：

- 這是本地端 local coding agent
- 環境是 VSCode + Continue + LM Studio
- 目前 repo_guardian MCP server 已能分析 repo
- Continue + MCP 已串起來
- 下一步目標是讓 agent 穩定走 `search → read → propose_patch → preview_diff` 流程

---

# 最後原則

請優先維持：

- sandbox safety
- session traceability
- tool consistency
- readable docs
- stable tests
- Continue / MCP 行為可重現
