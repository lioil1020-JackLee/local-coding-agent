# local-coding-agent

一個 **本地端、CLI-first、具備 Skill 系統** 的 coding agent 專案，目標是逐步打造出可媲美 **Cursor Agent** 的能力與體驗。

---

## 1. 專案定位

`local-coding-agent` 目前最準確的描述是：

> **以 `repo_guardian_mcp` 為主封裝與 CLI 入口的本地端 CLI Coding Agent（具備 Skill 系統）。**

根據目前 `pyproject.toml`，封裝的 package 是 `repo_guardian_mcp`，CLI script `repo-guardian` 也指向 `repo_guardian_mcp.cli:main`。因此，文件與開發認知都應以 `repo_guardian_mcp` 為主線，而不是把 `repo_guardian_agent` 寫成目前對外執行主體。

目前 repo 中可確認的主線能力包含：

- CLI 入口
- skill registry / skill metadata / manifest 基礎
- chat mode
- execution controller 與 orchestrator
- session / diff / rollback
- validation / sandbox
- trace summary
- analyze repo overview 與 safe edit 主力技能

---

## 2. 文件導覽

整併後的文件集中在 `docs/`，保留四份核心文件：

1. `01_架構總覽與導讀.md`
2. `02_產品定位與設計原則.md`
3. `03_執行架構與技術主線.md`
4. `04_開發流程_協作與進度.md`

建議閱讀順序：

1. 先看 `01_架構總覽與導讀.md`
2. 再看 `02_產品定位與設計原則.md`
3. 接著看 `03_執行架構與技術主線.md`
4. 最後看 `04_開發流程_協作與進度.md`

---

## 3. CLI 能力現況

### 基本命令
```bash
uv run repo-guardian skills
uv run repo-guardian plan . --prompt "請分析這個專案" --task-type analyze
uv run repo-guardian run . --prompt "請分析這個專案" --task-type analyze
uv run repo-guardian chat .
uv run repo-guardian session list .
uv run repo-guardian session resume . <real-session-id>
uv run repo-guardian diff . <real-session-id>
uv run repo-guardian rollback . <real-session-id>
```

### Chat mode
```bash
uv run repo-guardian chat .
uv run repo-guardian chat . --message "請分析這個專案" --once
```

在 chat 裡目前支援：

- `/help`
- `/skills`
- `/plan <text>`
- `/run <text>`
- `/apply`
- `/status`
- `/session list`
- `/session resume <id>`
- `/diff [session_id]`
- `/rollback [session_id]`
- `/exit`

若直接輸入自然語言，會優先走 session-aware routing。

---

## 4. Skill 系統現況

目前文件應採用這個描述：

> **skill system 已具備 v2 metadata 基礎，並已經出現更進一步的 metadata / manifest / chaining / fallback 能力；chat help 中亦以「skill registry v3 metadata」描述目前顯示內容。**

目前在代碼中可確認的 skill metadata / manifest 能力包含：

- `aliases`
- `examples`
- `routing_hints`
- `requires_session`
- `requires_validation`
- `priority`
- `enabled`
- `can_chain_to`
- `fallback_skills`
- `manifest_path`
- `SkillManifest`
- `from_dict()`
- `from_json_file()`
- `register_manifest()`

目前主力 skills 仍是：

- `analyze_repo`
- `safe_edit`

---

## 5. 執行架構摘要

目前主線可以簡化理解為：

`repo-guardian CLI`
→ `repo_guardian_mcp.cli`
→ `CLIAgentService` / `CLIChatService`
→ `SkillRegistry` / `ExecutionController`
→ orchestrators / runtime services
→ session / sandbox / validation / rollback / trace summary

這代表此專案已不只是單純的 safe-edit 腳本集合，也不只是單一 pipeline；它已具備本地 coding agent runtime 的主要骨架。

---

## 6. 關於 `repo_guardian_agent`

repo 內仍有 `repo_guardian_agent/` 目錄，這表示專案保留了另一組 agent 相關模組；但依目前 package 與 CLI script 主線來看，它不是目前對外封裝的核心入口。

因此 README 與 docs 應避免再把 `repo_guardian_agent` 寫成目前主要產品主體。

---

## 7. 測試與驗證

`tests/` 是正式測試目錄。文件應以目前 `tests/` 內容與本地實測結果為準，不再把某次歷史 `pytest` passed 數字永久寫死。

建議驗證方式：

```bash
uv run pytest
```

---

## 8. 下一步方向

從目前代碼與文件結構來看，最合理的後續方向包括：

1. skill registry / manifest / routing 持續演進
2. chat mode 與 session-aware workflow 持續加強
3. execution trace / trace summary 持續成為更穩定的結果整理層
4. safe edit / validation / rollback / session lifecycle 持續收斂成更完整的本地 coding agent runtime
