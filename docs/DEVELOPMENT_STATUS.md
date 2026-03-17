# DEVELOPMENT STATUS

## 目前狀態總結
目前專案已經從「只有概念與文件」進展到：

**MCP server + Continue + 安全修改流程 + 測試全綠**

簡單講，現在不是原型而已，
而是已經有一條能實際修改檔案、看 diff、做驗證、必要時回滾的主流程。

## 最新確認狀態
### 測試
- `pytest`：**14 passed**

### Continue / MCP
- 分析任務可成功走高階工具
- 修改任務可成功走 session workflow
- README 實際修改流程已測通

### 目前主線
1. `preview_user_request_plan_tool`
2. `create_task_session_tool`
3. `edit_file_tool`
4. `preview_session_diff_tool`
5. `run_validation_pipeline_tool`

## 本輪重要架構變更
### 1. sandbox 主線改為 copy-based
已不再把 git worktree 當作主要 sandbox 建立方式。

### 2. create / edit / diff / validation / rollback 已接成一條穩定主線
目前已可跑通完整安全修改流程。

### 3. Continue config 已能導向 Cursor-style workflow
- 分析先看 plan
- 修改先看 plan
- 再進 session workflow

## 已完成
- [x] MCP server 可正常啟動
- [x] 高階 agent 入口已建立
- [x] Continue config 已基本可用
- [x] copy-based sandbox 已接上
- [x] `run_task_pipeline` 已恢復穩定
- [x] `preview_session_diff` 已可配合 copy-based sandbox
- [x] `rollback_session` 已可用
- [x] `run_validation_pipeline` 已可用
- [x] pytest 全綠

## 目前尚未完成 / 下一步重點
### 高優先
- [ ] `ExecutionController`
- [ ] idempotent append / replace
- [ ] retry guard
- [ ] stop guard
- [ ] 更穩定的 tool fallback policy

### 中優先
- [ ] validation policy 分級
- [ ] 更好的 change report
- [ ] multi-file edit 的正式策略
- [ ] 更穩定的 diff contract

### 低優先
- [ ] 更完整的 patch planning
- [ ] 更像 Cursor 的摘要輸出
- [ ] 後續可考慮 PR / commit pipeline

## 目前最值得先做的事
### 第一優先
補 `ExecutionController`

### 第二優先
補 idempotent edit

### 第三優先
收斂 Continue 體驗
