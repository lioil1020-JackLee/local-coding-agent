# Agent 開發進度（2026-03）

本文件用於快速理解目前 repo-guardian / local-coding-agent 的實際完成度與下一步方向。

---

# ✅ 已完成（Stable）

## 1. Chat Mode v2（完整 CLI UX）
- `/session list`
- `/session resume`
- `/diff`
- `/rollback`
- `/status`
- 支援 `--once` 模式
- CLIChatService 穩定

## 2. Session Lifecycle
- create_task_session
- list_sessions
- pin_session
- resume_session
- rollback_session
- cleanup_sessions
- session metadata（pinned / resumable / expires）

## 3. Execution Pipeline
- run_task_pipeline
- skill selection
- validation pipeline
- safe_edit / analyze_repo
- execution_controller v1 + compat

## 4. Analyze 能力
- analyze_repo
- narrative_summary
- repo structure extraction
- file categorization

## 5. 測試覆蓋
- 約 60+ tests
- 全綠（pytest 通過）
- 涵蓋：
  - CLI
  - session lifecycle
  - execution pipeline
  - validation
  - agent loop（基礎）

---

# 🟡 已存在但未產品化

## execution_trace（重要）
目前 runtime 已產生：

```json
[
  {"step_type": "preview_plan"},
  {"step_type": "select_skill"},
  {"step_type": "execute_skill"},
  {"step_type": "validate_skill"},
  {"step_type": "finalize"}
]