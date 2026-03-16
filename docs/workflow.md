# Workflow

本文件描述 repo_guardian coding pipeline 的完整流程。

------------------------------------------------------------------------

# Session Lifecycle

create_task_session ↓ edit sandbox files ↓ preview diff ↓ run validation
↓ update session metadata ↓ query session status

------------------------------------------------------------------------

# Step 1 --- Create Task Session

Tool:

create_task_session

建立 sandbox worktree：

agent_runtime/sandbox_worktrees/`<session_id>`{=html}

並建立 session metadata：

agent_runtime/sessions/`<session_id>`{=html}.json

Session 初始狀態：

status = "active"

------------------------------------------------------------------------

# Step 2 --- Run Task Pipeline

Tool:

run_task_pipeline

支援三種修改方式。

Append mode="append"

Replace mode="replace"

Multi Operations operations = \[{...},{...}\]

------------------------------------------------------------------------

# Step 3 --- Diff Preview

Tool:

preview_session_diff

產生 git diff：

diff_text

------------------------------------------------------------------------

# Step 4 --- Validation

Validation hook：

run_validation_hook

v1 rule：

diff exists → pass

------------------------------------------------------------------------

# Step 5 --- Session Update

Service:

update_session_file

更新：

status edited_files changed summary validation

------------------------------------------------------------------------

# Step 6 --- Query Session Status

Tool:

get_session_status

Example response:

{ "status": "validated", "changed": true, "edited_files": \[...\],
"validation": {...} }

------------------------------------------------------------------------

# Typical Agent Usage

1 create_task_session 2 run_task_pipeline 3 preview_session_diff 4
get_session_status

------------------------------------------------------------------------

# Safety Model

sandbox edit ↓ diff preview ↓ validation ↓ apply (future)

------------------------------------------------------------------------

# Future Workflow (v2)

plan_change ↓ impact_analysis ↓ generate_patch ↓ apply_patch_to_sandbox
↓ run_tests ↓ validation ↓ apply_to_workspace
