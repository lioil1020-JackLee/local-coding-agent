# local-coding-agent

一個 **本地端、CLI-first、具備 Skill 系統** 的 coding agent 專案，目標是逐步打造出可在本地端安全操作 repo 的 agent workflow。

---

## 專案定位

目前從程式碼與封裝方式來看，這個專案最準確的描述是：

> **以 `repo_guardian_mcp` 為主執行入口的本地 CLI Coding Agent / Repo Guardian。**

它已經不只是單一 safe-edit 腳本集合，而是包含：

- CLI 命令入口
- skill registry 與 routing
- session / diff / rollback
- chat mode
- execution controller / orchestrator / trace summary
- validation 與 sandbox 相關服務

---

## 目前實際執行主線

目前對外可執行的主線是：

`repo-guardian` CLI  
→ `repo_guardian_mcp.cli`  
→ `CLIAgentService` / `CLIChatService`  
→ `SkillRegistry` / `ExecutionController` / runtime  
→ orchestrator / session / validation / trace services

其中：

- `repo_guardian_mcp` 是目前 **pyproject 已封裝、CLI script 已對接** 的主要套件
- `repo_guardian_agent` 目前仍存在於 repo 中，但不是 `pyproject.toml` 的 package 主線

---

## 文件導覽

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

## CLI 能力現況

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

### chat mode
```bash
uv run repo-guardian chat .
uv run repo-guardian chat . --message "請分析這個專案" --once
```

目前 chat 指令已包含：

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

若直接輸入自然語言，系統會優先走 session-aware routing。

---

## Skill 系統概況

目前文件應採用較保守但貼近實作的描述：

- skill metadata 已具備 **v2 基礎欄位**
- chat help 文字中已出現 **skill registry v3 metadata** 的說法
- 因此更準確的寫法是：**skill system 正在從 v2 metadata 基礎往更完整的 v3 能力演進**

現有程式中可確認的能力包含：

- `aliases`
- `examples`
- `routing_hints`
- `enabled`
- `priority`
- `can_chain_to`
- `fallback_skills`
- manifest model
- manifest 轉 metadata
- manifest 註冊能力

目前主力 skills 仍以：

- `analyze_repo`
- `safe_edit`

為核心。

---

## 架構補充

目前 `repo_guardian_mcp/services/` 已經形成主要服務層，包含但不限於：

- `cli_agent_service.py`
- `cli_chat_service.py`
- `execution_controller.py`
- `edit_execution_orchestrator.py`
- `task_orchestrator.py`
- `trace_summary_service.py`
- `validation_service.py`
- `session_service.py`
- `rollback_service.py`

因此文件描述應避免再把專案寫成「只有 pipeline」或「只有 MCP tools」。

---

## 測試與進度

`tests/` 仍是正式測試目錄，且目前 repo 中可看到多個和 trace / validation / session 相關測試檔。

由於測試數會變動，README 不再寫死單一 passed 數字；請以本地執行結果為準：

```bash
uv run pytest
```

---

## 下一步方向

從目前程式結構來看，最合理的後續方向包括：

1. skill registry / manifest / routing 持續演進
2. chat mode 與 agent session workflow 持續強化
3. execution trace / trace summary 成為更穩定的 single source of truth
4. safe edit / validation / session lifecycle 持續收斂成更完整的本地 coding agent runtime
