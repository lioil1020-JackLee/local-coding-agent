# Safe Editing Rules

這份規則是給 Continue / Builder 使用的安全修改準則。

## 核心原則

- 分析時絕對不能改檔。
- 修改時不能把聊天文字、說明文字、分析摘要寫進程式。
- 修改一定要走 repo_guardian 的安全流程，不要直接把內容寫進工作區檔案。
- 優先使用高階 agent 入口，不要先自己拼低階工具鏈。

## 高階主線

當使用者要求修改時，優先：

1. `repo_guardian_preview_user_request_plan_tool`
2. `repo_guardian_handle_user_request_tool`

只有高階入口失敗時，才退回低階工具。

## 低階後備主線

必要時才可依序使用：

1. `repo_guardian_run_task_pipeline_tool`
2. `repo_guardian_create_task_session_tool`
3. `repo_guardian_edit_file_tool`
4. `repo_guardian_preview_session_diff_tool`
5. `repo_guardian_run_validation_pipeline_tool`
6. `repo_guardian_rollback_session_tool`

## 禁止事項

- 不要把分析內容寫進 README、main.py、或任何原始碼檔案。
- 不要在沒有明確修改意圖時進入 edit mode。
- 不要略過 validation 就宣稱修改完成。
- 不要在沒有必要時自行改走 Continue 內建編輯。
- 不要因為工具可用就亂呼叫；要先符合意圖。

## 完成定義

一次修改任務至少要能交代：
- 做了哪些修改
- session_id 是什麼
- diff 摘要
- validation 結果
- 是否還在 sandbox
