# cursor_style_notes

## 目前已經證明可行的事
- Continue 可以走高階分析入口
- Continue 可以走安全修改 session workflow
- README 單檔修改已成功跑通
- validation 已能成功執行
- copy-based sandbox 已比 git worktree 更適合目前架構

## 為什麼目前的方向更像 Cursor
重點不是「模型自己很聰明」，而是：
- 先理解需求
- 再規劃步驟
- 再進安全修改流程
- 修改後看 diff
- 再驗證
- 必要時可回滾

這才是更接近 Cursor 的核心。

## 目前和 Cursor 還有差距的地方
- 還缺正式的 ExecutionController
- 還缺更穩定的 retry guard
- append 還要更 idempotent
- validation policy 還不夠細
- Continue 回覆節奏還可以再收斂

## 下一個最重要的大項
### ExecutionController
它會讓 repo_guardian 從：
- 一組能工作的工具

升級成：
- 真正的 agent backend

這是目前最值得優先做的項目。
