# CONTRIBUTING

## 目的

這份文件提供工程層面的貢獻規範。  
若你只想理解專案方向，請先看 `01_目標與方向.md`。  
若你準備實際修改程式碼，請讀這份文件。

---

## 專案目前的工程前提

本專案已具備：

- 可用的 CLI 命令
- skill system 雛形
- safe-edit pipeline
- session / sandbox 基礎
- `ExecutionController` 過渡主線
- 本地測試 `35 passed`

因此貢獻的首要原則是：

> **不要因為追求理想架構，而破壞現有可運作主線。**

---

## 修改前的基本問題清單

在送出任何重要修改前，請先回答：

1. 這個改動是否讓專案更接近本地端 CLI agent？
2. 這個改動是否與 skill system 相容？
3. 這個改動是否維持 safe-by-default？
4. 這個改動是否破壞 CLI 現有命令行為？
5. 這個改動是否破壞現有測試？

---

## 建議的修改流程

### 1. 先閱讀文件
最少請看：
- `00_文件導航.md`
- `01_目標與方向.md`
- `09_變更與進度.md`

若會碰 execution：
- `03_pipeline架構.md`
- `04_ExecutionController說明.md`

### 2. 再看相關程式與測試
不要只改程式不看測試。

### 3. 做小範圍、明確目的的修改
避免一次混入多種不同層級改動。

### 4. 執行本地測試
```bash
uv run pytest
```

### 5. 測 CLI
建議至少測：
```bash
uv run repo-guardian skills
uv run repo-guardian plan . --prompt "請分析這個專案" --task-type analyze
uv run repo-guardian run . --prompt "請分析這個專案" --task-type analyze
```

---

## 建議的提交粒度

### 好的提交
- skill system 改進
- controller 相容性修正
- CLI 子命令擴充
- 文件與 code 同步更新

### 不好的提交
- 一次重寫 controller + CLI + pipeline
- 改了使用者可見輸出卻不更新測試
- 只改 README 不更新 docs
- 只寫概念不落地

---

## 高風險修改區

以下區域屬於高風險區，請特別小心：

- `repo_guardian_mcp/services/execution_controller.py`
- `repo_guardian_mcp/services/cli_agent_service.py`
- `repo_guardian_mcp/skills.py`
- `repo_guardian_mcp/cli.py`
- `repo_guardian_mcp/services/edit_execution_orchestrator.py`
- `repo_guardian_mcp/tools/run_task_pipeline.py`

這些檔案直接影響：
- CLI 使用體驗
- agent loop
- skill flow
- pipeline 契約
- 測試穩定性

---

## 文件更新要求

任何會影響以下事項的改動，都應同步更新 docs：

- 產品定位
- CLI 命令
- skill 規格
- controller 流程
- pipeline 架構
- working baseline

因為本專案很依賴跨對話交接，若文件落後，之後的修改品質會快速下降。

---

## 命名與風格建議

### 命名
- CLI 命令名稱應穩定、清晰
- skill 名稱應用動作或能力導向命名
- 不要混用過多模糊縮寫

### 輸出
- 盡量使用結構化 JSON 或清楚可機器處理格式
- 確保 CLI 輸出穩定，避免頻繁破壞測試與腳本整合

### 程式風格
- 保持小函式、單一責任
- 把高階決策與底層執行分開
- 避免讓 CLI 直接耦合到底層實作細節

---

## 下一步最值得的工程投入

1. skill registry 與 metadata
2. CLI session 指令
3. richer validation summary
4. safe_edit skill 實用化
5. skill chaining 與 fallback

---

## 一句話總結

> **貢獻本專案時，請把自己當成是在打造一個可長期演進的本地端 CLI coding agent，而不是只是在補一個 Python 工具。**
