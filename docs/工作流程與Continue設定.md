# 工作流程與 Continue 設定

## 目的
這份文件要讓未來的新對話知道兩件事：
1. 這個專案目前實際開發流程是怎樣運作的
2. Continue.dev 在這個專案裡應該扮演什麼角色、什麼還沒做到

## 目前真實工作流程
使用者目前的工作流程大致如下：
- 在本地維護 `local-coding-agent`
- 透過 AI 協助做架構設計、模組調整、修 bug、補文件
- 使用者覆蓋本地檔案
- 本地執行 `uv run pytest`
- 再把專案同步到 Google Drive

Google Drive 在這裡的重要性不是當部署系統，而是作為跨對話上下文與專案版本狀態的持續同步來源。這代表未來新對話的助理如果能讀到相關文件，就應該優先利用這些文件恢復上下文。

## 目前已完成的開發主線
到這次更新為止，以下可以視為已完成或已穩定：
- session-based sandbox workflow
- validation / diff / rollback / session status 打通
- ExecutionController compatibility layer 穩定
- session lifecycle phase 1 接線完成
- 全套 pytest 綠燈（28 passed）

## Continue.dev 目前的定位
目前 Continue.dev 還不是整個系統的主控制中心。它更像是未來會深化整合的介面層／使用者互動層。

比較正確的理解方式是：
- 目前主線先把 backend execution、安全修改流程、session lifecycle 打穩
- Continue.dev 的深整合，應建立在 backend 已穩的前提之上

## 未來適合做的 Continue 整合方向
### 1. Session awareness
讓 Continue 能看到：
- current session
- session status
- changed files
- diff summary
- validation status

### 2. Safe-edit UX
讓 Continue 不只是直接發指令，而是明確呈現：
- 這次會不會建立新 session
- 會改哪些檔
- 驗證是否通過
- 是否可 rollback

### 3. Session lifecycle UX
未來應該讓 Continue 能操作：
- list sessions
- resume session
- pin session
- cleanup sessions

### 4. Multi-step execution visibility
如果後續導入 planner + executor，Continue 很適合顯示：
- 計畫步驟
- 執行中 step
- fallback / retry 狀態
- 最終 trace summary

## 目前不要做的事
目前不建議先把 Continue 整合做太深，原因有三個：
1. lifecycle 雖已接線，但還沒完全收斂到 orchestration 主入口
2. planner/executor 分層尚未正式完成
3. backend contract 還在從相容穩定層往更乾淨分層演進

## 對新對話的行動建議
若未來的新助理要做 Continue 相關工作，請先確認這些基礎已穩：
- 完整 pytest 仍為綠燈
- session lifecycle 在主入口行為一致
- `run_task_pipeline` 與 orchestrator 的責任邊界已明確

再來才適合做 Continue 深整合。

## 目前建議的順序
建議順序如下：
1. 先完成 session lifecycle deeper integration
2. 再做 planner + executor 正式接線
3. 最後再做 Continue.dev 深整合

這個順序和專案目前狀態一致，也比較不會讓 UI/IDE integration 放大 backend 未收斂的問題。
