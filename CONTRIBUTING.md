# CONTRIBUTING

本文件說明如何參與 local-coding-agent 專案。

但要注意：

這個專案的開發方式 **和一般開源專案不同**。

因為主要使用情境是：

**AI + 使用者協作開發**

而不是多人同時提交 PR。

---

# 專案目標

這個專案的目標是建立：

**本地端 Cursor-like coding agent**

而且必須符合以下條件：

1. 使用者不需要會寫程式
2. 可以用白話語言下指令
3. Agent 能自己理解 repo
4. Agent 能自己規劃修改步驟
5. 修改過程安全可控
6. 修改後可自動驗證
7. 必要時可 rollback

---

# 開發原則

## 1. 分析與修改必須分離

分析 repo 時：

- 不可修改任何檔案
- 只允許 read-only 操作

修改 repo 時：

- 必須透過安全 workflow
- 不可直接改原始檔

---

## 2. 安全修改流程 (必須遵守)

所有修改必須經過：

preview plan
→ create session
→ edit sandbox
→ preview diff
→ validation
→ rollback (必要時)

---

## 3. 不可把聊天文字寫進程式

AI 生成程式碼時：

不可把：

- 解釋文字
- prompt
- 對話內容

寫進程式碼。

---

## 4. 程式碼註解

所有新增程式碼：

必須使用

**繁體中文註解**

原因：

本專案主要使用者不是工程師。

---

# 專案結構

目前主要目錄：

```
repo_guardian_mcp/
    MCP server 與工具

continue/
    Continue 設定

docs/
    專案設計文件

tests/
    pytest 測試

agent_runtime/
    未來 agent runtime
```

---

# 如何參與開發

目前主要開發模式是：

**AI 協作式開發**

流程如下：

1. 使用者提出需求
2. AI 分析 repo
3. AI 修改指定檔案
4. 提供下載連結
5. 使用者覆蓋本地檔案
6. 執行測試
7. 回報結果
8. 繼續下一步

---

# Commit 建議格式

目前不強制，但建議：

```
feat: 新功能
fix: 修復 bug
refactor: 重構
docs: 文件更新
test: 測試更新
```

---

# 未來可能的貢獻方式

未來若專案公開，可能會接受：

- MCP tool 改進
- sandbox 改進
- validation policy
- agent planning 改進
- Continue integration

---

# 最重要的原則

這個專案的核心理念是：

**讓不會寫程式的人，也能安全地使用 coding agent。**
