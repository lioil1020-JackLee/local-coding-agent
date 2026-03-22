# local-coding-agent

本專案是 **本地端、CLI-first、繁體中文友善** 的 coding agent，主線目標是逼近 Cursor 體驗，但優先確保：

1. 分析不改檔
2. 修改可驗證、可回滾
3. 日常可穩定使用與維運

目前實際主線在 `repo_guardian_mcp/`，CLI 入口為 `repo-guardian`。

---

## 快速開始

```bash
uv run repo-guardian skills
uv run repo-guardian chat .
uv run repo-guardian run . --prompt "請分析這個專案" --task-type analyze
```

---

## 日常三條主線

### 1) 開發主線（分析/修改）

```bash
uv run repo-guardian chat .
uv run repo-guardian plan . --prompt "先幫我規劃" --task-type auto
uv run repo-guardian run . --prompt "幫我安全修改 README" --task-type edit
uv run repo-guardian diff . <session_id>
uv run repo-guardian rollback . <session_id>
```

### 2) Continue 主線（設定/驗證）

```bash
# 新手建議：一鍵 setup（會同步 config + rules + prompts，並保留備份）
uv run repo-guardian continue-config setup . --target-profile cursor
# 單獨診斷可用性（會回報分數、問題與修復建議）
uv run repo-guardian continue-config diagnose . --target-profile cursor
# 依診斷結果自動修復（可加 --dry-run 先預檢）
uv run repo-guardian continue-config autofix . --target-profile cursor
# 若修復中途失敗，會回報 error_code，並盡量自動還原（rollback）
uv run repo-guardian continue-config autofix . --target-profile cursor --run-e2e

uv run repo-guardian continue-config status --source-config continue/config.yaml --target-config F:\.continue\config.yaml
uv run repo-guardian continue-config sync --source-config continue/config.yaml --target-config F:\.continue\config.yaml --with-assets
uv run repo-guardian continue-e2e run .
```

### Continue 網路查證（雙引擎備援）

目前 `continue/config.yaml` 已配置：

1. `tavily-search`（主要）
2. `ddg-search`（次要備援）
3. 若兩者都不可用，規則會要求改走本機分析備援

說明：

1. `ddgs` 目前是透過外部 MCP 套件（`@oevortex/ddg_search`）接入
2. 專案內沒有另外落地一份 `ddgs` Python 實作檔

必要環境變數：

```bash
# Windows PowerShell（永久）
setx TAVILY_API_KEY "你的新金鑰"
```

完成後請重開 VS Code/Continue。

### 3) 維運主線（一鍵流程）

```bash
uv run repo-guardian ops run . --profile day-start --continue-source-config continue/config.yaml --continue-target-config F:\.continue\config.yaml
uv run repo-guardian ops run . --profile day-end --continue-source-config continue/config.yaml --continue-target-config F:\.continue\config.yaml --snapshot-tag day-end
uv run repo-guardian ops run . --profile release-check --continue-source-config continue/config.yaml --continue-target-config F:\.continue\config.yaml
```

---

## 進階命令（必要時）

```bash
# IDE bridge
uv run repo-guardian bridge invoke . --prompt "請分析此專案" --task-type analyze
uv run repo-guardian bridge queue . --limit 50
uv run repo-guardian bridge latest .

# 健康度與趨勢
uv run repo-guardian health report .
uv run repo-guardian health history . --limit 30
uv run repo-guardian health schedule-hint . --time 03:45 --task-name RepoGuardianHealthReport --refresh-benchmark

# runtime 清理
uv run repo-guardian runtime-cleanup run . --dry-run
uv run repo-guardian runtime-cleanup run . --aggressive
uv run repo-guardian runtime-cleanup schedule-hint . --time 03:30 --task-name RepoGuardianRuntimeCleanup

# benchmark / 觀測
uv run repo-guardian benchmark init .
uv run repo-guardian benchmark run . --threshold 0.85
uv run repo-guardian benchmark run . --tasks-file agent_runtime/benchmarks/corpus.v1.json --threshold 0.85
uv run repo-guardian benchmark report .
uv run repo-guardian observe routing .
```

---

## 文件導覽（不重複）

1. `docs/01_架構總覽與導讀.md`：你要先懂什麼、先做什麼
2. `docs/02_產品定位與設計原則.md`：系統分層與模組邊界
3. `docs/03_執行架構與技術主線.md`：安全執行與命令主線
4. `docs/04_開發流程_協作與進度.md`：交付節奏與檢查清單
5. `docs/05_安裝流程說明.md`：新機從 0 到可用的完整安裝與排查

---

## 目前狀態

- 已具備本地 agent 主線（CLI/chat/bridge/session/validation/rollback）
- 已具備 Continue 對齊主線（config sync + e2e）
- 已具備維運主線（health + ops + runtime cleanup）
- 已具備網路查證雙引擎（Tavily + DDG）與失敗備援鏈路
