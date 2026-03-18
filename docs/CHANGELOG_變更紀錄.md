# CHANGELOG

## 2026-03-19 - ExecutionController compatibility stabilized, session lifecycle phase 1 completed

### Summary
This project reached a meaningful stabilization point in this conversation. The core safe-edit pipeline was already working before this round, but the architecture was in a mixed state: the repo had both newer controller-style abstractions and older pipeline/orchestrator integrations still depending on legacy `ExecutionController` contracts. The main work completed in this conversation was to make those worlds compatible again, then connect the first stage of session lifecycle management into the existing workflow.

### Before this conversation
The project already had the following foundations in place:
- `ExecutionController` direction had been identified as the next important architecture layer.
- `EditExecutionOrchestrator` existed as the pipeline definition layer.
- Session-based sandbox editing workflow was already established.
- Validation, diff, rollback, and session status flows were already connected.
- `run_task_pipeline` had effectively become a wrapper around the internal orchestration flow.
- Core tests for the stable pipeline had already been passing before the compatibility regression introduced by the new controller file replacement.

### Problems encountered in this conversation
While extending the architecture, we initially replaced `repo_guardian_mcp/services/execution_controller.py` with a newer implementation that was conceptually cleaner but **not backward-compatible** with the existing repo.

This created a chain of failures because different parts of the project expected different controller contracts:
- newer tests expected handler-based execution with `handlers`, `RetryPolicy`, `FallbackPolicy`, and `ExecutionContext`
- older tests and older orchestration code expected symbols such as:
  - `ExecutionRequest`
  - `ExecutionPlan`
  - `ExecutionStatus`
  - `FailureKind.TRANSIENT`
  - `FailureKind.TOOLING`
  - `ExecutionStep(action=..., retry_limit=...)`
  - a controller that could be instantiated without the newer handler registry
- `run_task_pipeline -> task_orchestrator -> edit_execution_orchestrator` still depended on the older controller semantics

The first few patch attempts fixed missing symbols one by one, but that approach was not enough because the true issue was **interface drift across the whole project**.

### Key decision made
We switched from patching isolated missing names to a more correct approach:
1. inspect the full uploaded project zip
2. identify all real contracts around `execution_controller.py`
3. implement a compatibility layer that supports both new and old usage patterns

This was the turning point that restored the project.

### Final `ExecutionController` outcome
A compatibility-layer version of `repo_guardian_mcp/services/execution_controller.py` was produced and adopted.

That file now supports all of the following:
- newer handler-based controller tests
- older `ExecutionRequest / ExecutionPlan / ExecutionStatus` flows
- `EditExecutionOrchestrator` step-style usage
- `ExecutionStep` initialization using either the newer fields or older `action`, `retry_limit`, `fallback`, and related fields
- controller construction with or without handler injection
- retry and fallback support expected by newer tests
- mapping-like access patterns required by older orchestration code

### Session lifecycle phase 1 completed
After the controller compatibility work stabilized, the next completed step was the first stage of session lifecycle management.

Implemented in this conversation:
- `create_task_session` now records lifecycle-oriented metadata such as `last_accessed_at`, `expires_at`, and `pinned`
- `get_session_status` touches sessions so actively used sessions do not look stale
- `run_validation_pipeline` touches sessions
- `rollback_session` touches sessions
- session lifecycle tools were added or formalized:
  - `list_sessions`
  - `resume_session`
  - `pin_session`
  - `cleanup_sessions`
- session cleanup strategy was made explicit:
  - `days=3`
  - `max_sessions=20`
  - pinned sessions must be preserved
  - active/running sessions must not be removed
  - use both TTL and LRU, not one alone

### Bug fixed after lifecycle wiring
A regression was introduced in `run_validation_pipeline.py` during the lifecycle update. It had two issues:
1. a fallback diff helper referenced `repo_root_path` out of scope
2. a later fix accidentally wrote a broken `"\n"` join, causing a syntax error (`unterminated string literal`)

Both problems were fixed. The final validation pipeline now:
- keeps fallback diff scoped correctly
- does not perform session touching inside the fallback helper
- leaves session-touching in the main flow
- passes validation-related tests again

### Test results reached in this conversation
Final local result reported by the user:
- `uv run pytest`
- **28 passed in 15.82s**

This is the current known-good baseline.

### Architectural status at end of this conversation
Current project state should be understood as:
- the stable safe-edit pipeline is intact
- `ExecutionController` is no longer an isolated experiment; it is now a compatibility layer that protects both old and new interfaces
- session lifecycle has entered real implementation, not just design
- disk control is now a real tracked concern in architecture, not just a future note

### Next recommended milestones
Recommended next work, in order:
1. integrate `resume/list/cleanup` usage more directly into `run_task_pipeline` and higher-level orchestration flows
2. centralize session metadata updates so touch/update logic is not duplicated across tools
3. introduce planner-driven multi-step task execution on top of the now-stable controller layer
4. deepen Continue.dev integration after lifecycle behavior becomes stable
5. consider a more explicit memory/state layer only after planner + lifecycle are stable

### Important note for future conversations
If a future assistant opens this repository in a new conversation, it should **not** assume `ExecutionController` can be redesigned freely. The controller file is currently serving as a compatibility boundary for multiple generations of project code. Any refactor must start by checking:
- `tests/test_execution_controller.py`
- `tests/test_execution_controller_v1.py`
- `repo_guardian_mcp/services/edit_execution_orchestrator.py`
- `repo_guardian_mcp/services/task_orchestrator.py`
- `repo_guardian_mcp/tools/run_task_pipeline.py`

Breaking that compatibility layer will likely reintroduce the failures that were solved here.
