# Repo Guardian 開發狀態

最後更新：2026-03-17

## 已完成

- MCP server
- session service
- sandbox edit service
- diff preview service
- validation service
- rollback service

目前所有測試通過。

pytest → 14 passed

---

## 架構調整

系統正從：

run_task_pipeline_tool

轉換為：

create_task_session_tool  
edit_file_tool  
preview_session_diff_tool  
run_validation_pipeline_tool  
rollback_session_tool  

目標：

避免 Continue MCP tool timeout。

---

## 已知問題

使用新工具鏈時，sandbox workspace 有時不會自動初始化。

Agent 可能會看到 session 狀態：

pending_workspace

未來將改善 sandbox 自動建立機制。

---

## 下一步計畫

1. sandbox workspace 自動初始化
2. 簡化 edit pipeline
3. 改善 session metadata
4. 強化 validation hooks
5. 增加 MCP integration tests