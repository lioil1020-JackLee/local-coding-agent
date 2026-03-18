# CONTRIBUTING

## Purpose of this document
This repository is being developed in an iterative human + AI collaboration style. This file is not only about coding conventions; it also records **how work should continue safely across conversations**.

The most important thing for future contributors and future AI assistants to understand is that this project is **not a toy refactor sandbox**. It is an active architecture-in-progress with a working safe-edit pipeline. New work must preserve that working baseline.

## Project philosophy
The project exists to make a local coding agent usable in a safe, controlled way. The design is intentionally conservative around file mutation.

Core principles:
- analysis and modification should be separate concerns
- all modifications happen in a sandbox/session copy, not directly in the source repo
- session metadata is the single source of truth for lifecycle and recovery state
- diff / validation / rollback are not optional extras; they are part of the default safety path
- tool layer and control/orchestration layer should stay decoupled

## Current architecture reality
At the time of this document update, the repo contains both:
- older pipeline/orchestrator flows
- newer controller-style abstractions

Do not assume that one has completely replaced the other.

In practice, the current project depends on a compatibility layer around `ExecutionController`. That compatibility layer exists because:
- newer tests expect handler-based execution semantics
- older tests and orchestration code still expect legacy request/plan/status symbols and step APIs

If you modify `repo_guardian_mcp/services/execution_controller.py`, you must first verify the full contract surface.

## Required safety rule before changing controller/orchestrator code
Before editing any of the following files, inspect them together:
- `repo_guardian_mcp/services/execution_controller.py`
- `repo_guardian_mcp/services/edit_execution_orchestrator.py`
- `repo_guardian_mcp/services/task_orchestrator.py`
- `repo_guardian_mcp/tools/run_task_pipeline.py`
- `tests/test_execution_controller.py`
- `tests/test_execution_controller_v1.py`
- `tests/test_run_task_pipeline.py`
- `tests/test_validation_pipeline.py`
- `tests/test_rollback_session.py`

Reason: these files collectively define the real execution contract.

## Collaboration workflow used in this project
The user typically works like this:
1. AI proposes architecture or implementation direction
2. AI prepares directly replaceable files
3. user overwrites the local repo manually
4. user runs local pytest on Windows / PowerShell / uv
5. user reports traceback or green results back
6. AI adjusts based on the real local state
7. user syncs the updated project state to Google Drive

This means future assistants should optimize for:
- producing replacement-ready files
- keeping patches focused and traceable
- being explicit about which files to overwrite
- respecting the local test loop as the ground truth

## Testing expectations
At this point, the known good baseline is:
- `uv run pytest`
- result: **28 passed**

Any meaningful architectural change must preserve that baseline or explain exactly why a test contract is being changed.

### Minimum suggested test loop
For risky execution changes:
1. targeted tests for the affected area
2. full `uv run pytest`

For docs-only work, full test is not required, but it is still useful if code was touched in the same patch.

## Session lifecycle expectations
The project now has real lifecycle management, not just design notes.

Current expected behavior:
- sessions track metadata such as `last_accessed_at`, `expires_at`, and `pinned`
- cleanup strategy uses both TTL and LRU
- default retention target is 3 days
- default max session count is 20
- pinned sessions are preserved
- active/running sessions should not be deleted

When editing lifecycle-related code, preserve these expectations unless the architecture docs are intentionally updated in the same change.

## Documentation expectations
When updating docs, do not write only short summaries. The docs in this project are also intended to help a future conversation recover context without reading the entire chat history.

Good docs for this project should answer:
- what has already been completed
- what was attempted and failed
- what design decisions were made and why
- what the current stable baseline is
- what the next recommended milestone is
- what future assistants must not accidentally break

## What not to do
Avoid these common mistakes:
- replacing the controller with a clean new design without preserving old contracts
- bypassing the sandbox/session safety model for convenience
- introducing direct repo mutations as a shortcut
- moving lifecycle state out of session metadata without a full migration plan
- editing many files at once without identifying which tests validate the change
- writing docs that are too brief to act as cross-conversation handoff material

## Preferred style for future patches
When preparing a patch for the user:
- state exactly which files are new vs overwrite
- include short run commands for verification
- explain risks honestly
- prefer compatibility-preserving changes unless a deliberate migration is underway

## Current recommended next work
The recommended next sequence is:
1. strengthen session lifecycle integration in orchestration entry points
2. reduce duplicated session-touch logic
3. add planner-driven multi-step execution above the stable controller layer
4. deepen Continue.dev integration
5. add richer memory/state only after the above are stable
