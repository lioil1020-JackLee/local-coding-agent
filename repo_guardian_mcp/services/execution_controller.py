from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from inspect import signature
from typing import Any, Iterable, Mapping, Protocol, runtime_checkable


class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"
    ERROR = "error"


class ExecutionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    STOPPED = "stopped"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class FailureKind(str, Enum):
    UNKNOWN = "unknown"
    TRANSIENT = "transient"
    PERMANENT = "permanent"
    TOOL = "tool"
    TOOLING = "tooling"
    VALIDATION = "validation"
    ROLLBACK = "rollback"
    SESSION = "session"
    GUARD = "guard"
    RETRY_EXHAUSTED = "retry_exhausted"
    USER = "user"
    SYSTEM = "system"


@dataclass
class RetryPolicy:
    max_attempts: int = 1
    per_step_max_retries: dict[str, int] = field(default_factory=dict)
    retry_on_kinds: tuple[FailureKind, ...] = field(default_factory=tuple)
    retry_on_exceptions: tuple[type[BaseException], ...] = field(default_factory=tuple)

    def get_max_retries(self, step_type: str) -> int:
        if step_type in self.per_step_max_retries:
            return max(0, int(self.per_step_max_retries[step_type]))
        return max(0, int(self.max_attempts) - 1)

    def should_retry(self, step: "ExecutionStep", result: "StepResult", attempt: int) -> bool:
        max_retries = self.get_max_retries(step.step_type)
        if attempt > max_retries:
            return False
        if result.status not in {StepStatus.FAILED, StepStatus.ERROR}:
            return False
        if not self.retry_on_kinds:
            return True
        return bool(result.failure_kind and result.failure_kind in self.retry_on_kinds)


@dataclass
class StopPolicy:
    stop_on_statuses: tuple[StepStatus, ...] = (StepStatus.FAILED, StepStatus.ERROR)

    def should_stop(self, step: "ExecutionStep", result: "StepResult") -> bool:
        return result.status in self.stop_on_statuses


@dataclass
class FallbackPolicy:
    enabled: bool = False
    fallback_step_names: tuple[str, ...] = field(default_factory=tuple)
    activate_on_kinds: tuple[FailureKind, ...] = field(default_factory=tuple)

    def get_fallback_steps(self, step: "ExecutionStep", result: "StepResult") -> list["ExecutionStep"]:
        return []

    def should_activate(self, result: "StepResult") -> bool:
        if not self.enabled:
            return False
        if not self.activate_on_kinds:
            return result.status in {StepStatus.FAILED, StepStatus.ERROR}
        return bool(result.failure_kind and result.failure_kind in self.activate_on_kinds)


@dataclass
class ExecutionStep:
    step_id: str = ""
    step_type: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    name: str | None = None
    action: str | None = None
    handler: Any | None = None
    retry_limit: int = 0
    retry: RetryPolicy | None = None
    fallback: FallbackPolicy | None = None
    enabled: bool = True
    description: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.action:
            self.action = self.step_type or self.name or self.step_id or "step"
        if not self.step_type:
            self.step_type = self.action or self.name or self.step_id or "step"
        if not self.name:
            self.name = self.action or self.step_type or self.step_id or "step"
        if not self.step_id:
            self.step_id = self.name or self.action or self.step_type or "step"
        if self.retry is None and self.retry_limit > 0:
            self.retry = RetryPolicy(max_attempts=self.retry_limit + 1)

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any], index: int = 0) -> "ExecutionStep":
        payload = dict(raw.get("payload") or {})
        passthrough_keys = {
            "step_id",
            "id",
            "step_type",
            "type",
            "name",
            "action",
            "payload",
            "description",
            "metadata",
            "handler",
            "retry_limit",
            "retry",
            "fallback",
            "enabled",
        }
        for key, value in raw.items():
            if key not in passthrough_keys:
                payload.setdefault(key, value)
        return cls(
            step_id=str(raw.get("step_id") or raw.get("id") or raw.get("name") or raw.get("action") or f"step_{index}"),
            step_type=str(raw.get("step_type") or raw.get("type") or raw.get("action") or raw.get("name") or f"step_{index}"),
            payload=payload,
            name=raw.get("name"),
            action=raw.get("action"),
            handler=raw.get("handler"),
            retry_limit=int(raw.get("retry_limit", 0) or 0),
            retry=raw.get("retry"),
            fallback=raw.get("fallback"),
            enabled=bool(raw.get("enabled", True)),
            description=raw.get("description"),
            metadata=dict(raw.get("metadata") or {}),
        )


@dataclass
class ExecutionPlan:
    steps: list[ExecutionStep] = field(default_factory=list)
    plan_id: str | None = None
    summary: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    task_type: str | None = None
    requires_session: bool = False
    requires_validation: bool = False
    allow_rollback: bool = False

    def __post_init__(self) -> None:
        self.steps = [_normalize_step(step, i) for i, step in enumerate(self.steps, start=1)]


@dataclass
class ExecutionRequest:
    steps: list[ExecutionStep] = field(default_factory=list)
    request_id: str | None = None
    user_request: str = ""
    summary: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    operations: list[dict[str, Any]] = field(default_factory=list)
    task_type: str = "edit"
    repo_root: str | None = None

    def __post_init__(self) -> None:
        raw_steps: list[Any] = list(self.steps)
        if not raw_steps and self.operations:
            raw_steps = list(self.operations)
        self.steps = [_normalize_step(step, i) for i, step in enumerate(raw_steps, start=1)]

    @property
    def plan_id(self) -> str | None:
        return self.request_id


@dataclass
class StepResult:
    status: StepStatus = StepStatus.SUCCESS
    output: Any = field(default_factory=dict)
    error: str | None = None
    failure_kind: FailureKind | None = None
    retryable: bool = False
    message: str | None = None
    summary: str | None = None
    updates: dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.status in {StepStatus.SUCCESS, StepStatus.SKIPPED}

    @classmethod
    def success(cls, **output: Any) -> "StepResult":
        return cls(status=StepStatus.SUCCESS, output=dict(output))

    @classmethod
    def skipped(cls, **output: Any) -> "StepResult":
        return cls(status=StepStatus.SKIPPED, output=dict(output))

    @classmethod
    def failed(
        cls,
        error: str,
        *,
        failure_kind: FailureKind = FailureKind.UNKNOWN,
        retryable: bool = False,
        **output: Any,
    ) -> "StepResult":
        return cls(
            status=StepStatus.FAILED,
            output=dict(output),
            error=error,
            failure_kind=failure_kind,
            retryable=retryable,
            message=error,
            summary=error,
        )


@dataclass
class ExecutionTraceItem:
    step_id: str
    step_type: str
    status: StepStatus
    error: str | None = None
    retry_count: int = 0
    failure_kind: FailureKind | None = None
    output: Any = field(default_factory=dict)


@dataclass
class StepRunRecord:
    name: str
    action: str
    ok: bool
    status: StepStatus
    output: Any = field(default_factory=dict)
    error: str | None = None


class ExecutionContext:
    def __init__(
        self,
        task_id: str = "task",
        user_request: str = "",
        session_id: str | None = None,
        state: dict[str, Any] | None = None,
        trace: list[ExecutionTraceItem] | None = None,
        metadata: dict[str, Any] | None = None,
        stopped: bool = False,
        error: str | None = None,
        status: StepStatus = StepStatus.PENDING,
    ) -> None:
        self.task_id = task_id
        self.user_request = user_request
        self.session_id = session_id
        self.state: dict[str, Any] = dict(state or {})
        self.trace: list[ExecutionTraceItem] = list(trace or [])
        self.metadata: dict[str, Any] = dict(metadata or {})
        self.stopped = stopped
        self.error = error
        self.status = status

    @property
    def ok(self) -> bool:
        return not self.stopped and self.error is None

    def get(self, key: str, default: Any = None) -> Any:
        return self.state.get(key, default)

    def __getitem__(self, key: str) -> Any:
        return self.state[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.state[key] = value

    def update(self, values: Mapping[str, Any]) -> None:
        self.state.update(values)


@dataclass
class ExecutionOutcome:
    context: ExecutionContext

    @property
    def success(self) -> bool:
        return self.context.ok

    @property
    def ok(self) -> bool:
        return self.context.ok

    @property
    def error(self) -> str | None:
        return self.context.error

    @property
    def trace(self) -> list[ExecutionTraceItem]:
        return self.context.trace


@dataclass
class LegacyExecutionResult:
    ok: bool
    status: ExecutionStatus
    steps: list[StepRunRecord] = field(default_factory=list)
    session_id: str | None = None
    final_output: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


@runtime_checkable
class StepHandler(Protocol):
    def can_handle(self, step_type: str) -> bool: ...
    def run(self, step: ExecutionStep, ctx: ExecutionContext) -> StepResult: ...


class ExecutionController:
    def __init__(
        self,
        handlers: Iterable[Any] | dict[str, Any] | None = None,
        retry_policy: RetryPolicy | None = None,
        stop_policy: StopPolicy | None = None,
        fallback_policy: FallbackPolicy | None = None,
        **legacy_dependencies: Any,
    ) -> None:
        self.handlers = handlers or []
        self.retry_policy = retry_policy or RetryPolicy()
        self.stop_policy = stop_policy or StopPolicy()
        self.fallback_policy = fallback_policy or FallbackPolicy()
        self.legacy = legacy_dependencies

    def execute(
        self,
        plan_or_steps: ExecutionPlan | ExecutionRequest | Iterable[ExecutionStep | Mapping[str, Any]] | None = None,
        ctx: ExecutionContext | None = None,
        *,
        steps: Iterable[ExecutionStep | Mapping[str, Any]] | None = None,
        initial_state: Mapping[str, Any] | None = None,
        **context_kwargs: Any,
    ) -> ExecutionContext:
        selected = steps if steps is not None else plan_or_steps
        if selected is None:
            raise TypeError("execute() 需要 plan_or_steps 或 steps")

        if ctx is None:
            ctx = ExecutionContext(**context_kwargs)
        elif context_kwargs:
            for key, value in context_kwargs.items():
                setattr(ctx, key, value)
        if initial_state:
            ctx.update(dict(initial_state))
        ctx.status = StepStatus.RUNNING

        original_steps = self._normalize_steps(selected)
        step_map: dict[str, ExecutionStep] = {}
        for step in original_steps:
            step_map[step.step_id] = step
            if step.name:
                step_map[step.name] = step
            if step.action:
                step_map[step.action] = step
        queue = [step for step in original_steps if step.enabled]

        while queue:
            step = queue.pop(0)
            final_result: StepResult | None = None
            attempts = 0
            step_retry_policy = step.retry or (RetryPolicy(max_attempts=step.retry_limit + 1) if step.retry_limit > 0 else self.retry_policy)
            max_retries = step_retry_policy.get_max_retries(step.step_type)

            while True:
                try:
                    raw_result = self._run_step(step, ctx)
                    result = _normalize_result(raw_result)
                except Exception as exc:
                    failure_kind = FailureKind.TOOLING
                    result = StepResult(
                        status=StepStatus.FAILED,
                        error=str(exc),
                        message=str(exc),
                        summary=str(exc),
                        failure_kind=failure_kind,
                    )
                final_result = result
                self._append_trace(ctx, step, result, retry_count=attempts)

                if result.ok:
                    self._merge_step_success(ctx, step, result)
                    break

                attempts += 1
                if attempts > max_retries or not step_retry_policy.should_retry(step, result, attempts):
                    break

            assert final_result is not None
            if not final_result.ok:
                fallback_steps = self._resolve_fallback_steps(step, final_result, step.fallback, step_map)
                if fallback_steps:
                    queue = fallback_steps + queue
                    continue
                if self.stop_policy.should_stop(step, final_result):
                    ctx.stopped = True
                    ctx.error = final_result.error or final_result.message
                    ctx.status = StepStatus.FAILED
                    return ctx

        ctx.status = StepStatus.SUCCESS if ctx.error is None else StepStatus.FAILED
        return ctx

    def execute_plan(self, plan: ExecutionPlan | ExecutionRequest, ctx: ExecutionContext | None = None, **kwargs: Any) -> ExecutionContext:
        return self.execute(plan, ctx=ctx, **kwargs)

    def execute_steps(self, steps: Iterable[ExecutionStep | Mapping[str, Any]], ctx: ExecutionContext | None = None, **kwargs: Any) -> ExecutionContext:
        return self.execute(steps=steps, ctx=ctx, **kwargs)

    def execute_request(self, request: ExecutionRequest, ctx: ExecutionContext | None = None, **kwargs: Any) -> ExecutionContext:
        if ctx is None:
            ctx = ExecutionContext(task_id=request.request_id or "task", user_request=request.user_request, metadata=dict(request.metadata))
        if request.repo_root:
            ctx.state.setdefault("repo_root", request.repo_root)
        return self.execute(request, ctx=ctx, **kwargs)

    def run(
        self,
        request: ExecutionRequest | ExecutionPlan | Iterable[ExecutionStep | Mapping[str, Any]] | None = None,
        *,
        steps: Iterable[ExecutionStep | Mapping[str, Any]] | None = None,
        initial_state: Mapping[str, Any] | None = None,
        ctx: ExecutionContext | None = None,
        **kwargs: Any,
    ) -> LegacyExecutionResult | ExecutionOutcome:
        if isinstance(request, ExecutionRequest) and self.legacy.get("planner") is not None:
            return self._run_legacy_request(request)
        selected = steps if steps is not None else request
        return ExecutionOutcome(self.execute(selected, ctx=ctx, initial_state=initial_state, **kwargs))

    def _run_legacy_request(self, request: ExecutionRequest) -> LegacyExecutionResult:
        planner = self.legacy["planner"]
        plan = planner.build_execution_plan(request)
        state: dict[str, Any] = {
            "task_type": request.task_type,
            "user_request": request.user_request,
            "repo_root": request.repo_root,
        }
        state.update(dict(request.metadata))
        steps_out: list[StepRunRecord] = []
        session_id: str | None = None
        final_output: dict[str, Any] = {}

        for step in plan.steps:
            action = step.action or step.step_type
            attempts = 0
            max_retries = step.retry_limit
            while True:
                attempts += 1
                try:
                    ok, output, error = self._invoke_legacy_action(action, state)
                except Exception as exc:
                    ok, output, error = False, {}, str(exc)
                if ok:
                    if isinstance(output, Mapping):
                        state.update(dict(output))
                        if "session_id" in output:
                            session_id = output["session_id"]
                    steps_out.append(StepRunRecord(name=step.name or action, action=action, ok=True, status=StepStatus.SUCCESS, output=output))
                    if action == "analyze":
                        final_output["analysis"] = output
                    elif action == "validate":
                        final_output["validation"] = output
                    elif action == "preview_diff":
                        final_output["diff"] = output
                    break
                if attempts <= max_retries:
                    continue
                steps_out.append(StepRunRecord(name=step.name or action, action=action, ok=False, status=StepStatus.FAILED, output=output, error=error))
                if action == "validate" and plan.allow_rollback and session_id:
                    rollback_service = self.legacy.get("rollback_service")
                    if rollback_service is not None:
                        rollback_service.rollback_session(session_id)
                    return LegacyExecutionResult(
                        ok=False,
                        status=ExecutionStatus.ROLLED_BACK,
                        steps=steps_out,
                        session_id=session_id,
                        final_output=final_output,
                        error=error,
                    )
                return LegacyExecutionResult(
                    ok=False,
                    status=ExecutionStatus.STOPPED,
                    steps=steps_out,
                    session_id=session_id,
                    final_output=final_output,
                    error=error,
                )

        return LegacyExecutionResult(
            ok=True,
            status=ExecutionStatus.SUCCESS,
            steps=steps_out,
            session_id=session_id,
            final_output=final_output,
        )

    def _invoke_legacy_action(self, action: str, state: dict[str, Any]) -> tuple[bool, Any, str | None]:
        if action == "preview_plan":
            return True, {"message": "preview ready"}, None
        if action == "create_session":
            service = self.legacy.get("session_service")
            result = service.create_task_session(state.get("repo_root"), metadata=None)
            return bool(result.get("ok")), result, None if result.get("ok") else result.get("message") or result.get("error")
        if action == "edit":
            service = self.legacy.get("edit_orchestrator")
            result = service.edit(state)
            return bool(result.get("ok")), result, None if result.get("ok") else result.get("message") or result.get("error")
        if action == "preview_diff":
            service = self.legacy.get("edit_orchestrator")
            result = service.preview_diff(state)
            return bool(result.get("ok")), result, None if result.get("ok") else result.get("message") or result.get("error")
        if action == "validate":
            service = self.legacy.get("validation_service")
            result = service.run_validation(state)
            return bool(result.get("ok")), result, None if result.get("ok") else result.get("message") or result.get("error")
        if action == "analyze":
            service = self.legacy.get("analysis_executor")
            result = service.analyze(state)
            return True, result, None
        return False, {}, f"unknown action: {action}"

    def _normalize_steps(self, value: ExecutionPlan | ExecutionRequest | Iterable[ExecutionStep | Mapping[str, Any]]) -> list[ExecutionStep]:
        if isinstance(value, (ExecutionPlan, ExecutionRequest)):
            return [_normalize_step(step, i) for i, step in enumerate(value.steps, start=1)]
        return [_normalize_step(step, i) for i, step in enumerate(value, start=1)]

    def _run_step(self, step: ExecutionStep, ctx: ExecutionContext) -> Any:
        if step.handler is not None:
            return self._call_handler(step.handler, step, ctx)
        handler = self._resolve_handler(step.step_type)
        return self._call_handler(handler, step, ctx)

    def _resolve_handler(self, step_type: str) -> Any:
        if isinstance(self.handlers, dict):
            return self.handlers.get(step_type) or self.handlers.get("*")
        for handler in self.handlers:
            can_handle = getattr(handler, "can_handle", None)
            if callable(can_handle) and can_handle(step_type):
                return handler
            step_types = getattr(handler, "STEP_TYPES", None)
            if step_types and (step_type in step_types or "*" in step_types):
                return handler
        return None

    def _call_handler(self, handler: Any, step: ExecutionStep, ctx: ExecutionContext) -> Any:
        if handler is None:
            payload = step.payload
            if callable(payload):
                return payload(step, ctx)
            return payload
        if hasattr(handler, "run") and callable(handler.run):
            return handler.run(step, ctx)
        if hasattr(handler, "handle") and callable(handler.handle):
            return handler.handle(step, ctx)
        if callable(handler):
            try:
                sig = signature(handler)
                arity = len(sig.parameters)
            except Exception:
                arity = 2
            if arity >= 2:
                try:
                    return handler(step, ctx)
                except TypeError:
                    pass
            return handler(ctx.state)
        raise TypeError(f"step handler 不可執行: {handler!r}")

    def _merge_step_success(self, ctx: ExecutionContext, step: ExecutionStep, result: StepResult) -> None:
        output = result.output
        if isinstance(output, Mapping):
            ctx.state[step.step_id] = dict(output)
            if step.name:
                ctx.state[step.name] = dict(output)
            if step.action:
                ctx.state[step.action] = dict(output)
            ctx.state.update(dict(output))
            if "session_id" in output:
                ctx.session_id = output["session_id"]
        else:
            ctx.state[step.step_id] = output
            if step.name:
                ctx.state[step.name] = output
            if step.action:
                ctx.state[step.action] = output
        if result.updates:
            ctx.state.update(result.updates)
            if "session_id" in result.updates:
                ctx.session_id = result.updates["session_id"]

    def _resolve_fallback_steps(
        self,
        step: ExecutionStep,
        result: StepResult,
        step_fallback: FallbackPolicy | None,
        step_map: dict[str, ExecutionStep],
    ) -> list[ExecutionStep]:
        if step_fallback and step_fallback.should_activate(result):
            names = step_fallback.fallback_step_names
            resolved = []
            for name in names:
                src = step_map.get(name)
                if src is None:
                    continue
                resolved.append(_clone_step_enabled(src))
            if resolved:
                return resolved
        controller_fallbacks = self.fallback_policy.get_fallback_steps(step, result)
        return [_normalize_step(item, 0) for item in controller_fallbacks]

    def _append_trace(self, ctx: ExecutionContext, step: ExecutionStep, result: StepResult, retry_count: int) -> None:
        ctx.trace.append(
            ExecutionTraceItem(
                step_id=step.step_id,
                step_type=step.step_type,
                status=result.status,
                error=result.error,
                retry_count=retry_count,
                failure_kind=result.failure_kind,
                output=result.output,
            )
        )


def _clone_step_enabled(step: ExecutionStep) -> ExecutionStep:
    return ExecutionStep(
        step_id=step.step_id,
        step_type=step.step_type,
        payload=dict(step.payload),
        name=step.name,
        action=step.action,
        handler=step.handler,
        retry_limit=step.retry_limit,
        retry=step.retry,
        fallback=step.fallback,
        enabled=True,
        description=step.description,
        metadata=dict(step.metadata),
    )


def _normalize_step(raw: Any, index: int) -> ExecutionStep:
    if isinstance(raw, ExecutionStep):
        return raw
    if isinstance(raw, Mapping):
        return ExecutionStep.from_dict(raw, index=index)
    raise TypeError(f"無法辨識的 ExecutionStep 型別: {type(raw)!r}")


def _normalize_result(result: Any) -> StepResult:
    if isinstance(result, StepResult):
        return result
    if isinstance(result, Mapping):
        raw_status = result.get("status")
        if raw_status is None:
            raw_status = StepStatus.SUCCESS if result.get("ok", True) else StepStatus.FAILED
        try:
            status = raw_status if isinstance(raw_status, StepStatus) else StepStatus(str(raw_status))
        except ValueError:
            status = StepStatus.SUCCESS if result.get("ok", True) else StepStatus.FAILED
        raw_failure_kind = result.get("failure_kind")
        failure_kind = None
        if raw_failure_kind is not None:
            try:
                failure_kind = raw_failure_kind if isinstance(raw_failure_kind, FailureKind) else FailureKind(str(raw_failure_kind))
            except ValueError:
                failure_kind = FailureKind.UNKNOWN
        output = dict(result.get("output") or {})
        updates = dict(result.get("updates") or {})
        summary = result.get("summary") or result.get("message")
        for key, value in result.items():
            if key not in {"status", "output", "error", "failure_kind", "retryable", "message", "summary", "updates", "ok"}:
                output.setdefault(key, value)
        return StepResult(
            status=status,
            output=output,
            error=result.get("error") or (None if result.get("ok", True) else result.get("message")),
            failure_kind=failure_kind,
            retryable=bool(result.get("retryable", False)),
            message=result.get("message") or result.get("error"),
            summary=summary,
            updates=updates,
        )
    if result is None:
        return StepResult.failed("handler returned None", failure_kind=FailureKind.UNKNOWN)
    if isinstance(result, bool):
        return StepResult.success(ok=True) if result else StepResult.failed("handler returned False", failure_kind=FailureKind.PERMANENT)
    return StepResult.success(value=result)


__all__ = [
    "ExecutionContext",
    "ExecutionController",
    "ExecutionOutcome",
    "ExecutionPlan",
    "ExecutionRequest",
    "ExecutionStatus",
    "ExecutionStep",
    "ExecutionTraceItem",
    "FailureKind",
    "FallbackPolicy",
    "LegacyExecutionResult",
    "RetryPolicy",
    "StepHandler",
    "StepResult",
    "StepRunRecord",
    "StepStatus",
    "StopPolicy",
]
