# Pipeline Architecture v1

ExecutionController：
- 控制 step flow
- retry / fallback
- state 管理

EditExecutionOrchestrator：
- 定義 steps
- 對外 contract

原則：
- step 不直接改 context
- 用 updates 回寫
