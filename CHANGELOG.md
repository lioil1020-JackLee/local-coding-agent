# CHANGELOG

本文件記錄 local-coding-agent 專案的重要變更。
目的是讓未來的對話或開發者可以快速了解：
- 什麼時候做了哪些架構決策
- 哪些功能已經完成
- 哪些功能還在規劃

格式不追求嚴格 SemVer，主要是**實際開發里程碑**。

---

# 2026-03 (目前主要開發階段)

## 核心架構建立

已建立完整的 **local coding agent 基礎架構**：

- MCP server (`repo_guardian_mcp`)
- Continue integration
- 安全修改 workflow
- session sandbox
- diff / validation / rollback pipeline

這一輪的重點不是功能數量，而是**建立可長期維護的架構基礎**。

---

## 新增

### MCP tools

新增並整合以下工具：

- `preview_user_request_plan_tool`
- `handle_user_request_tool`
- `create_task_session_tool`
- `edit_file_tool`
- `preview_session_diff_tool`
- `run_validation_pipeline_tool`
- `rollback_session_tool`

這些工具組成 **安全修改流程 (safe edit pipeline)**。

---

### 安全修改流程 (Safe Edit Workflow)

正式建立以下流程：

1. preview plan
2. create session
3. 建立 sandbox
4. edit file
5. preview diff
6. run validation
7. rollback (必要時)

目標：

讓 agent 修改程式碼時具備 **可檢查、可回復、可控制風險** 的能力。

---

### copy-based sandbox

原本嘗試使用 `git worktree` 作為 sandbox。

實際測試後發現：

- Continue + MCP tool call 容易 timeout
- worktree 建立成本高
- rollback 較慢

因此正式改為：

**copy-based sandbox 主線**

優點：

- 建立速度快
- 結構簡單
- 更適合本地 agent workflow

---

### Continue integration

Continue 已成功接入 repo_guardian MCP。

目前已能：

- 分析 repo
- 找入口點
- 修改 README
- 預覽 diff
- 執行 validation
- rollback session

---

### 測試

目前 pytest 狀態：

14 passed

代表目前核心 workflow 已可穩定運作。

---

## 目前已知問題

目前仍需改善的地方：

### 1. append 重複問題

某些情況下 append 可能重複寫入。

之後會新增：

- append_if_missing
- replace_once

確保修改操作 **idempotent**。

---

### 2. retry / stop policy

目前 agent 在某些錯誤情況下可能：

- 不必要 retry
- fallback 到不相關流程

未來將加入：

- retry guard
- stop guard

---

### 3. ExecutionController (尚未實作)

未來將新增：

ExecutionController

負責：

- step-by-step execution
- retry control
- stop policy
- fallback policy

這會讓 repo_guardian 從：

「一組工具」

升級為：

「真正的 agent backend」。

---

## 未來 roadmap (高優先)

下一階段開發重點：

1. ExecutionController
2. idempotent edit
3. validation policy 分級
4. Continue 體驗收斂

---

# 專案目標 (長期)

本專案的目標不是做一個 prompt demo。

而是建立：

**本地端 Cursor-like coding agent**

並具備：

- 白話語言指令
- repo 自動理解
- 安全修改
- 自動驗證
- 可回滾
- 長期可維護架構
