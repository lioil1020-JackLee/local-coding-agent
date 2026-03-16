# Builder 工具規則

修改任務時請遵守：

1. 優先使用 `repo_guardian run_task_pipeline_tool`。
2. 如果使用者只是要小幅修改單一檔案，不要先做長篇分析。
3. 不要自行規劃成多個 MCP 工具鏈，除非 `run_task_pipeline_tool` 明確不適用。
4. 成功後要回覆：
   - 使用了哪些 repo_guardian 工具
   - session_id
   - diff 摘要
5. 若失敗，直接回覆錯誤，不要假裝完成。
