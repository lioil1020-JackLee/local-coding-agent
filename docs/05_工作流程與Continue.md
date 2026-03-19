# 工作流程與 Continue

## 這份文件的目的

這份文件要說明兩件事：

1. 本專案目前實際是怎麼被開發、測試與使用的
2. Continue 在新的產品定位下，應該被放在什麼位置

因為若不把這兩件事分清楚，專案很容易再度失焦。

---

## 目前實際工作流程

本專案目前真實的工作模式，大致如下：

1. 在本地 repo 中進行設計與開發
2. 使用 AI 協助產出或修正程式與文件
3. 將檔案覆蓋到本地 repo
4. 在本地執行：
   - `uv run pytest`
   - `uv run repo-guardian skills`
   - `uv run repo-guardian plan ...`
   - `uv run repo-guardian run ...`
5. 根據本地結果繼續修正
6. 最後同步專案與文件

這代表一件很重要的事情：

> **本地 repo 的真實測試結果才是最後真相。**

---

## 目前已驗證可用的 CLI 行為

截至目前，CLI 已至少具備以下能力：

### 列出 skills
```bash
uv run repo-guardian skills
```

### 預覽計畫
```bash
uv run repo-guardian plan . --prompt "請分析這個專案" --task-type analyze
```

### 執行分析
```bash
uv run repo-guardian run . --prompt "請分析這個專案" --task-type analyze
```

這代表 CLI 已不是空殼，而是實際可操作的 agent 表面。

---

## Continue 在專案中的正確定位

Continue 很重要，但它不是本專案的唯一中心。

### 更正確的定位是：
- Continue = 重要互動介面層之一
- CLI = 主產品介面之一
- backend/runtime = 真正能力核心

如果把 Continue 當成專案主體，會有幾個問題：

1. backend 會被迫依附特定互動介面
2. skill system 抽象容易被 IDE UX 綁死
3. CLI 產品面會被弱化
4. agent runtime 的獨立性變差

---

## 在新定位下，Continue 最適合做什麼

### 1. 顯示計畫
讓使用者更容易看到 plan 與 skill selection。

### 2. 顯示 diff / validation
Continue 很適合作為結果可視化層。

### 3. 顯示 session 狀態
例如：
- current session
- validation status
- changed files
- rollback availability

### 4. 提供 human-in-the-loop 互動
未來若 CLI / agent 增加確認點，Continue 也很適合承接部分互動體驗。

---

## 為什麼現在仍應以 CLI 為主

因為 CLI 具備幾個優勢：

- 最容易自動化
- 最容易測試
- 最不依賴特定 editor
- 最適合當 agent 的穩定外部契約
- 最適合逐步產品化

一個真正成熟的本地端 coding agent，應該先在 CLI 成形，再自然長到 IDE。

---

## 建議的產品層次

### 核心層
- session / sandbox
- validation
- rollback
- controller
- pipeline
- skills

### 產品層
- CLI
- Continue integration
- 未來其他 IDE / automation integration

### 結論
Continue 很重要，但它應該建立在 CLI 與 runtime 已穩定的基礎上，而不是反過來。

---

## 下一步最合理的整合方向

1. 先擴充 CLI 命令：
   - `session list`
   - `session resume`
   - `diff`
   - `rollback`
   - `chat`
2. skill system 成熟後，再讓 Continue 顯示：
   - selected skill
   - execution trace
   - validation summary
3. 最後再做更深的 editor interaction

---

## 一句話總結

> **Continue 是重要介面層，但 local-coding-agent 的主體必須是本地端 CLI agent runtime；CLI 應先成熟，再把能力向 IDE 可視化延伸。**
