# local-coding-agent

一個 **本地端、CLI-first、具備 Skill 系統** 的 coding agent 專案，目標是逐步打造出可媲美 **Cursor Agent** 的能力與體驗。

---

## 1. 專案定位

`local-coding-agent` 的長期定位是：

> **本地端 CLI Coding Agent（具備 Skill 系統）**

目前它已具備：
- safe-edit runtime
- session / diff / rollback
- skill registry v2 基礎結構
- chat mode 初版
- analyze 第二輪降噪後的 repo overview
- 穩定測試基準

---

## 2. CLI 能力現況

### 基本命令
```bash
uv run repo-guardian skills
uv run repo-guardian plan . --prompt "請分析這個專案" --task-type analyze
uv run repo-guardian run . --prompt "請分析這個專案" --task-type analyze
uv run repo-guardian session list .
uv run repo-guardian diff . <real-session-id>
uv run repo-guardian rollback . <real-session-id>
```

### chat mode 初版
```bash
uv run repo-guardian chat .
```

單次訊息模式：
```bash
uv run repo-guardian chat . --message "請分析這個專案" --once
```

在 chat 裡目前支援：
- `/help`
- `/skills`
- `/plan <text>`
- `/run <text>`
- `/exit`

若直接輸入自然語言，預設會走 plan。

> 在 PowerShell 請直接輸入真實 session id，不要輸入 `<session-id>` 這種尖括號佔位符。

---

## 3. Skill registry v2 基礎結構

目前 skill metadata 已從 v1 升級到 v2 基礎結構，新增：

- `aliases`
- `examples`
- `routing_hints`
- `enabled`

目前 registry 已支援：
- `list_skill_metadata()`
- `find_by_capability()`
- 依 priority 排序
- 顯式 skill name / alias 查找
- 基於 task type 與文字 hints 的初步 routing

### 目前 skills
#### analyze_repo
- `version: 2.0`
- `capabilities: ["repo_analysis", "repo_overview"]`

#### safe_edit
- `version: 2.0`
- `capabilities: ["safe_edit", "file_edit", "validation"]`

---

## 4. analyze 第二輪降噪

目前 analyze 已排除：
- `.git`
- `.venv`
- `__pycache__`
- `node_modules`
- `build`
- `dist`
- `agent_runtime/sandbox_workspaces`
- `agent_runtime/snapshots`
- `agent_runtime/sessions`
- `*.egg-info`
- `.coverage`

並提供：
- `top_level_entries`
- `key_files`
- `category_counts`
- `important_modules`

這讓 analyze 更接近真正可用的 repo overview。

---

## 5. 本地測試基準

```bash
uv run pytest
```

目前結果：

- **40 passed**

這是目前 working baseline。

---

## 6. 下一步方向

最值得的下一步：

1. skill registry v2.5 / v3
   - manifest
   - dynamic registration
   - chaining
   - fallback routing

2. chat mode 升級
   - session-aware chat
   - `/apply`
   - `/diff`
   - `/rollback`
   - 更好的 human-in-the-loop 互動

3. analyze narrative summary
   - 用人類更好讀的摘要敘述 repo 結構與入口\n