# Pipeline Architecture

## Why this document exists
This file should help a future conversation understand the current execution pipeline without needing the full prior chat history.

The project already has a functioning safe-edit pipeline. Recent work did not replace that pipeline; instead, it stabilized and extended it.

## Current architectural shape
The current system should be understood as layered, but still in transition.

### Stable parts already in production use inside the repo
- sandbox/session-based edit workflow
- diff generation
- validation pipeline
- rollback support
- session status management
- run-task wrapper entry point

### Architecture direction now being actively implemented
- clearer controller layer
- improved session lifecycle management
- future planner/executor separation
- future deeper Continue.dev integration

This means the project is not in a blank-slate state. It already has working operational paths that must remain green while the architecture evolves.

## Main execution path today
A simplified mental model of the main modify flow is:

1. receive user/tool request
2. normalize request into task/pipeline input
3. create or use a session sandbox
4. execute file edits inside the sandbox
5. preview diff
6. run validation
7. if needed, allow rollback
8. expose status/results back to the caller

This is the important part: the pipeline is already functional and tested. Architectural work should strengthen this path, not bypass it.

## Key modules involved
The exact code may evolve, but these modules are currently load-bearing:
- `repo_guardian_mcp/tools/run_task_pipeline.py`
- `repo_guardian_mcp/services/task_orchestrator.py`
- `repo_guardian_mcp/services/edit_execution_orchestrator.py`
- `repo_guardian_mcp/services/execution_controller.py`
- session, diff, validation, and rollback related services/tools

## Role of `run_task_pipeline`
`run_task_pipeline` is effectively the user-facing wrapper into the current internal orchestration flow. Even if more sophisticated planning is added later, this entry point matters because tests and current usage patterns still rely on it.

## Role of `EditExecutionOrchestrator`
`EditExecutionOrchestrator` is where the actual pipeline intent is expressed. In practice, it represents how the system thinks about safe edit operations:
- preview/plan-like preparation
- session creation
- edit execution
- diff preview
- validation
- rollback handling when required

## Role of `ExecutionController`
The controller is currently not just a clean new abstraction. It is a compatibility boundary that allows:
- newer controller-style tests to pass
- older pipeline integrations to continue functioning

That makes it architecturally important but also sensitive.

## Session model
The sandbox/session model is one of the defining design decisions of this project.

Important assumptions:
- edits happen in a copied/sandboxed workspace, not directly in the source repo
- session metadata is the single source of truth for lifecycle and recovery state
- rollback depends on preserving the correct session relationship to sandbox state
- session status is not just UI metadata; it affects operational correctness

## Session lifecycle phase 1
This conversation added the first meaningful lifecycle-management layer.

What is now expected:
- sessions store `last_accessed_at`
- sessions store `expires_at`
- sessions can be pinned
- validation/status/rollback flows can refresh access time
- tools exist to list, resume, pin, and clean sessions

This is important because the project had already started suffering from workspace growth caused by copy-based session sandboxes.

## Disk-control strategy
The cleanup strategy now documented for the project is:
- default retention window: 3 days
- default max sessions: 20
- pinned sessions are preserved
- active/running sessions are preserved
- use TTL + LRU together

Reasoning:
- TTL alone is not enough because active work may still be relevant
- LRU alone is not enough because stale sessions may accumulate forever
- pinned sessions are required for debugging, demos, or intentionally preserved work

## What has been proven by tests
At the end of this conversation, the user reported a full green baseline:
- `uv run pytest`
- **28 passed**

This means the current architecture is not theoretical; it is supported by the local test loop.

## Architectural constraints for future work
Future work should respect these constraints:
- do not break the safe-edit pipeline while introducing planner/controller improvements
- do not detach session lifecycle from session metadata without a migration plan
- do not assume controller and orchestrator layers can be rewritten independently
- do not treat docs as lightweight summaries; they also serve as cross-conversation handoff material

## Most sensible next step
The most sensible next implementation step after this document is:
1. integrate session lifecycle behavior deeper into orchestration entry points
2. reduce duplicated session-touch logic
3. only then move into fuller planner/executor architecture

That order matters because the project already has a working pipeline and real disk-pressure concerns.
