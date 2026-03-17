# Workflow

## Current Execution Flow

User → run_task_pipeline → TaskOrchestrator → EditExecutionOrchestrator → ExecutionController → Steps

## Step Execution Model

- StepContext input
- dict / StepResult output
- ExecutionController handles retry/stop/fallback

## Next Evolution

- Orchestrators become pipeline builders only
