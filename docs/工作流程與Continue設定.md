# 工作流程與 Continue 設定

## 目的
這份文件要幫未來的新對話理解兩件事：

1. 目前這個專案的真實工作流程是什麼  
2. Continue.dev 在新的產品定位下，應該被放在什麼位置  

現在專案的終極目標已明確為：

> **本地端 CLI Agent（具備 Skill 系統），並以能力可媲美 Cursor Agent 為目標。**

因此 Continue 不再應被誤認為整個系統唯一的中心，而應被理解為**重要介面層之一**。

---

## 目前真實工作流程
使用者目前的工作方式大致如下：

- 在本地維護 `local-coding-agent`
- 透過 AI 協助做架構設計、模組調整、修 bug、補文件
- 使用者覆蓋本地檔案
- 本地執行 `uv run pytest`
- 再把專案同步到 Google Drive

Google Drive 的角色主要是：
- 跨對話上下文同步
- 專案狀態保留
- 文件 handoff 來源

---

## 在新定位下，Continue 的正確角色
目前比較正確的理解是：

### 核心產品方向
- 本地端 CLI agent
- skill system
- safe-edit runtime
- session lifecycle
- planner / executor 演進

### Continue 的角色
- IDE/聊天介面層
- session / diff / validation / trace 的展示層
- 未來 skill 執行可視化入口之一
- 不是唯一也不是最底層主控制中心

---

## 為什麼先不要把 Continue 當主軸
因為專案目前真正需要先穩住的是：

1. session lifecycle 更完整整合
2. controller / orchestrator / pipeline 的責任邊界
3. planner + executor 的正式接線
4. skill abstraction

若這些還沒穩，就先把 Continue 做太深，反而容易放大 backend contract 未收斂的問題。

---

## 未來適合做的 Continue 整合方向

### 1. Session awareness
讓 Continue 能看到：
- current session
- session status
- changed files
- diff summary
- validation status

### 2. Safe-edit UX
明確呈現：
- 是否建立新 session
- 會改哪些檔
- 驗證是否通過
- 是否可 rollback

### 3. Skill execution visibility
如果導入 skill system，Continue 很適合顯示：
- 選中了哪個 skill
- skill 執行步驟
- 失敗與 fallback 狀態
- trace summary

### 4. Multi-step agent execution visibility
未來 planner / executor 完整化後，可顯示：
- 計畫步驟
- 目前進度
- retry / fallback
- 最終結果摘要

---

## 專案主體仍應是 CLI
最重要的是：

> Continue 是重要介面，但**CLI 才是主產品表面之一**。

這與新目標一致，也更符合「本地端 CLI Agent」的終極定位。

---

## 建議順序
1. 先完成 session lifecycle deeper integration
2. 再補 planner + executor
3. 再導入 skill abstraction
4. 之後強化 CLI UX
5. 最後再做 Continue 深整合
