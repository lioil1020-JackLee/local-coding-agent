# 工作流程與 Continue 設定

本文件說明兩件事：

1. local-coding-agent 目前建議採用的工作流程
2. Continue 在這個專案裡扮演什麼角色，以及設定時應注意什麼

本文件特別重要，因為目前很多誤解都來自於：
- 設計中的流程
- 已實作的流程
- Continue 實際生效的設定
三者沒有被清楚區分。

---

## 一、先講結論：目前主線工作流是什麼

目前最應該被視為主線的工作流，是：

```text
preview plan
→ create session
→ edit / propose patch / stage patch
→ preview diff
→ run validation
→ rollback（必要）
```

這條線的核心精神是：

- 先規劃
- 不直接碰主 repo
- 所有寫入先進 sandbox
- 先看 diff
- 再驗證
- 失敗能回滾

---

## 二、分析任務與修改任務必須分流

### 1. 分析任務
例如：
- 幫我看懂這個專案
- 入口點在哪
- 幫我整理架構
- 找某個函式在哪裡
- 這個 repo 在做什麼

#### 分析任務原則
- 優先走唯讀工具
- 不修改檔案
- 不建立不必要副作用
- 以聊天或文件輸出整理結果

#### 分析任務常見流程
```text
接收需求
→ repo overview / search codebase / entrypoint / code region
→ 整理結果
→ 回傳白話說明
```

### 2. 修改任務
例如：
- 幫我改這個功能
- 幫我實作
- 套用修改
- 直接開始改

#### 修改任務原則
- 先說明理解與風險
- 進入 session workflow
- 必須有 diff 與 validation 概念
- 不可直接把聊天內容寫進 repo

---

## 三、為什麼要從大型 pipeline 轉向多工具 session workflow

早期思路比較傾向：
- 一個大工具把所有事情一次做完

看起來方便，但實務上會有幾個問題：

1. Continue / MCP 環境下容易 timeout
2. 中途失敗難以定位在哪一步
3. fallback 容易亂跳
4. 每個步驟責任不清
5. 使用者也難理解現在進行到哪裡

因此目前更推薦：
- 拆工具
- 拆步驟
- 把副作用控制在小範圍
- 讓流程可追蹤

---

## 四、目前建議的修改流程（詳細版）

### Step 1：preview plan
目的：
- 先把使用者需求轉成可執行步驟
- 判斷要分析還是修改
- 避免一上來直接改錯方向

### Step 2：create session
目的：
- 建立隔離工作空間
- 讓本次任務有 session_id
- 為後續 diff / validation / rollback 提供基礎

### Step 3：edit / propose patch / stage patch
目的：
- 在 sandbox 內實際形成修改
- 這一步可能是直接安全編輯，也可能是 patch proposal + stage

### Step 4：preview diff
目的：
- 讓系統與使用者都能看到實際改了什麼
- 這一步是安全流程的關鍵，不應省略

### Step 5：run validation
目的：
- 確認修改至少通過基本檢查
- 避免把顯然有問題的內容當作成功

### Step 6：rollback（必要時）
目的：
- 若修改失敗、驗證失敗、或流程需要回復，能恢復安全狀態

---

## 五、目前 `run_task_pipeline` 應如何理解

`run_task_pipeline` 的角色很容易被誤解。

### 不應把它理解成
- 萬能黑盒
- 什麼都丟進去就一定能穩定完成
- 永遠比小工具流程更好

### 比較合理的理解
它是：
- 一個較高層的統一入口
- 幫助分析 / 編輯任務快速起步
- 在某些情況下方便
- 但仍需和 session workflow 的主線角色區分清楚

因此未來文件與實作應更明確界定：
- 何時推薦用 `run_task_pipeline`
- 何時應走手動 session workflow
- 何時應只產生 patch proposal，不直接套用

---

## 六、Continue 在這個專案中的角色

Continue 在本專案中不只是「一個前端」，它其實同時扮演：

1. 自然語言入口
2. 模型分工落點
3. 工具流程限制器
4. 使用者體驗界面
5. 專案導覽與修改任務切換器

---

## 七、Continue 設定的核心目的

目前 config 不只是放：
- 模型名稱
- API base
- timeout

更重要的是，它負責定義：

### 1. analysis-first
預設先分析，不要直接改檔。

### 2. 專案導覽模式
當使用者說：
- 幫我看懂這個專案
- 入口點在哪
- 幫我抓重點

應自動進入專案導覽 / 分析模式，而不是要求使用者先指定檔名。

### 3. 修改任務的工具約束
當使用者真的要修改時，應優先走 repo_guardian MCP tools 與 session workflow，而不是亂用其他不受控編輯方式。

### 4. 模型分工
例如：
- qwen25-main：偏分析與規劃
- qwen25-builder：偏修改與實作

這種分工對穩定性很重要。

---

## 八、Continue 設定時的實務注意事項

### 1. 先確認哪一份 config 真正生效
實務上常見問題不是 config 有沒有寫，而是：
- 到底哪一份在生效？
- 本地與同步來源是否一致？
- 是專案內 config 還是使用者層 config？

目前你已確認本地與同步路徑會同步，因此後續可把同步來源視為最新版本來源。

### 2. 設定內容要反映真實主線
如果目前主線是 session workflow，那 config 裡就應明確引導：
- 分析任務走分析工具
- 修改任務走 session workflow
- 避免大工具 timeout 路線被當成預設

### 3. 設定要避免過度理想化
文件裡若提到 `.continue/config.json` + HTTP endpoint 形式，應明確標註：
- 哪些是理想設計
- 哪些是目前已實作
- 哪些是未來規劃

避免使用者以為所有東西都已完整產品化。

---

## 九、建議的 Continue / Agent 任務分流

### A. 使用者只是想理解專案
建議：
- 走分析模式
- 用 repo overview / search / entrypoint
- 不建立不必要 session
- 不產生 patch

### B. 使用者想先規劃再修改
建議：
- 先 preview plan
- 找出會影響哪些檔案
- 再決定是否建立 session

### C. 使用者明確要修改
建議：
- create session
- edit / patch
- preview diff
- validation
- rollback（必要時）

### D. 使用者只要 patch proposal，不要直接改
建議：
- search / code region
- propose patch
- preview diff
- 停在 proposal 層，不直接套用

---

## 十、目前文件應如何描述 Continue 狀態才準確

比較準確的描述應是：

- Continue 已可與 repo_guardian MCP 流程配合
- config 已承擔重要流程約束職責
- 分析模式與修改模式已有規則分流
- session workflow 已是主線設計
- 但完整產品化體驗仍在持續收斂中

而不是簡單寫成：
- 「已整合完成」就結束

因為「已接通」和「已成熟」不是同一件事。

---

## 十一、未來應該持續補強的部分

### 1. 更清楚的工具選擇策略
讓 Continue 不只是能叫工具，而是更穩定知道該先叫哪個工具。

### 2. 更少 timeout 與亂 fallback
這需要：
- 工具責任更清楚
- Controller 更成熟
- config 規則更精準

### 3. 更完整的進度與狀態回報
例如：
- 現在在哪一步
- 哪個步驟失敗
- 是否已 rollback
- validation 哪裡沒過

### 4. 更好的使用者可理解性
使用者不應被迫理解：
- tool name
- patch internals
- session metadata 細節

而應看到：
- 白話計畫
- 可理解 diff
- 可理解驗證結果
- 明確下一步

---

## 十二、總結

目前工作流程與 Continue 設定的核心，不是讓系統看起來複雜，而是要建立一件事：

> **讓代理的行為更可控，讓修改更安全，讓使用者更容易理解。**

因此後續若再調整 workflow 或 config，請優先檢查：

- 是否更符合分析 / 修改分流
- 是否更符合 session workflow 主線
- 是否更降低 timeout 風險
- 是否更容易讓未來維護者接手
