# Validation Policy

本文件描述 repo_guardian coding agent 在執行修改後的 **驗證策略
(validation policy)**。

Validation 的目標：

-   確保修改確實產生變更
-   避免 agent 產生空 patch
-   為未來的 test / lint / typecheck 預留擴充點

------------------------------------------------------------------------

# Validation Pipeline (v1)

目前 v1 的 validation pipeline 非常簡單：

edit sandbox file ↓ generate diff ↓ check diff exists ↓ validation pass
/ fail

------------------------------------------------------------------------

# Current Rule

目前唯一的 rule：

diff 存在 → validation pass\
diff 不存在 → validation fail

Example:

pass:

README.md + new line

fail:

(no change)

------------------------------------------------------------------------

# Validation Output

Validation 會寫入 session metadata：

agent_runtime/sessions/`<session_id>`{=html}.json

Example:

{ "status": "pass", "passed": true, "checks": \[ { "name":
"diff_present", "status": "pass", "message": "Diff detected in sandbox
session." } \], "summary": "Validation passed: diff detected." }

------------------------------------------------------------------------

# Validation Status

session 可能有以下狀態：

active validated failed

------------------------------------------------------------------------

# Future Validation (v2)

未來 validation pipeline 可能包含：

pytest ruff / flake8 mypy security scan format check

未來流程可能會變成：

edit ↓ diff ↓ lint ↓ tests ↓ typecheck ↓ validation result
