# local-coding-agent

一個 **本地端、CLI-first、具備 Skill 系統** 的 coding agent 專案，目標是逐步打造出可媲美 **Cursor Agent** 的能力與體驗。

---

## 專案定位

`local-coding-agent` 的長期定位是：

> **本地端 CLI Coding Agent（具備 Skill 系統）**

目前已具備：

- safe-edit runtime
- session / diff / rollback
- skill registry v2 基礎結構
- chat mode 初版至進一步演進版本
- analyze 能力與 repo overview
- 穩定測試基準

---

## 文件導覽

整併後的文件集中在 `docs/`，只保留四份核心文件：

1. `01_架構總覽與導讀.md`
   - 給新加入的開發者或新的 AI 助理快速建立心智模型
   - 說明建議閱讀順序、文件之間的關係，以及高風險區域

2. `02_產品定位與設計原則.md`
   - 說明專案的最終方向
   - 整理 local-first、CLI-first、agent-first、skill-enabled、safe-by-default 等原則

3. `03_執行架構與技術主線.md`
   - 說明 pipeline、orchestrator、ExecutionController、trace summary 的角色分工
   - 釐清哪些是穩定底座、哪些是過渡層、哪些是未來演進方向

4. `04_開發流程_協作與進度.md`
   - 合併開發流程、協作原則、貢獻規範、變更紀錄與目前進度
   - 作為日常開發與 handoff 的單一入口

---

## CLI 能力現況

### 基本命令
```bash
uv run repo-guardian skills
uv run repo-guardian plan . --prompt "請分析這個專案" --task-type analyze
uv run repo-guardian run . --prompt "請分析這個專案" --task-type analyze
uv run repo-guardian session list .
uv run repo-guardian diff . <real-session-id>
uv run repo-guardian rollback . <real-session-id>
```

### Chat mode
```bash
uv run repo-guardian chat .
```

單次訊息模式：
```bash
uv run repo-guardian chat . --message "請分析這個專案" --once
```

在 chat 裡目前支援或逐步支援：

- `/help`
- `/skills`
- `/plan <text>`
- `/run <text>`
- `/status`
- `/session list`
- `/session resume <id>`
- `/diff [session_id]`
- `/rollback [session_id]`
- `/exit`

> 在 PowerShell 請直接輸入真實 session id，不要輸入 `<session-id>` 這種尖括號佔位符。

---

## Skill 系統概況

目前 skill metadata 已升級到 v2 基礎結構，支援：

- `aliases`
- `examples`
- `routing_hints`
- `enabled`
- capability / alias / hint routing
- priority-based ordering

目前主要 skills：

### analyze_repo
- `version: 2.0`
- `capabilities: ["repo_analysis", "repo_overview"]`

### safe_edit
- `version: 2.0`
- `capabilities: ["safe_edit", "file_edit", "validation"]`

---

## Analyze 能力

目前 analyze 已逐步排除雜訊目錄，並提供：

- `top_level_entries`
- `key_files`
- `category_counts`
- `important_modules`
- 後續版本中的 narrative summary 能力方向

---

## 測試基準

```bash
uv run pytest
```

working baseline 以本地實測為準；詳細進度、測試數與演進紀錄請見 `docs/04_開發流程_協作與進度.md`。

---

## 下一步方向

最值得投入的方向包括：

1. skill registry v2.5 / v3
2. chat / CLI UX 升級
3. richer agent loop
4. analyze narrative summary
5. 更穩定的 execution trace / trace summary
