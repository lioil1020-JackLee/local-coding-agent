from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Protocol
from uuid import uuid4


class ExecutionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    ERROR = "error"
    STOPPED = "stopped"
    RETRYING = "retrying"
    ROLLBACK_REQUESTED = "rollback_requested"
    ROLLED_BACK = "rolled_back"
    PARTIAL = "partial"
    HIGH_RISK_FAILURE = "high_risk_failure"


StepStatus = ExecutionStatus


class FailureKind(str, Enum):
    UNKNOWN = "unknown"
    TRANSIENT = "transient"
    VALIDATION = "validation"
    NON_RETRYABLE = "non_retryable"
    TOOL_ERROR = "tool_error"
    TOOLING = "tool_error"
    SESSION_ERROR = "session_error"
    EDIT_ERROR = "edit_error"
    DIFF_ERROR = "diff_error"
    ROLLBACK_ERROR = "rollback_error"


@dataclass
class RetryPolicy:
    max_attempts: int = 1
    retryable_kinds: tuple[FailureKind, ...] = (FailureKind.TRANSIENT, FailureKind.SESSION_ERROR)
    retry_on_kinds: tuple[FailureKind, ...] | None = None
    retry_on_exceptions: tuple[type[BaseException], ...] = ()
    allow_unknown_retry: bool = False

    def should_retry(self, failure_kind: FailureKind, attempt: int) -> bool:
        if attempt >= self.max_attempts:
            return False
        effective_kinds = self.retry_on_kinds if self.retry_on_kinds is not None else self.retryable_kinds
        if failure_kind in effective_kinds:
            return True
        if failure_kind == FailureKind.UNKNOWN and self.allow_unknown_retry:
            return True
        return False

    def should_retry_exception(self, exc: BaseException, attempt: int) -> bool:
        if attempt >= self.max_attempts:
            return False
        return bool(self.retry_on_exceptions and isinstance(exc, self.retry_on_exceptions))


@dataclass
class FallbackPolicy:
    enabled: bool = False
    allowed_failure_kinds: tuple[FailureKind, ...] = ()
    activate_on_kinds: tuple[FailureKind, ...] | None = None
    fallback_actions: tuple[str, ...] = ()
    fallback_step_names: tuple[str, ...] = ()

    def can_fallback(self, failure_kind: FailureKind) -> bool:
        if not self.enabled:
            return False
        effective_kinds = self.activate_on_kinds if self.activate_on_kinds is not None else self.allowed_failure_kinds
        if not effective_kinds:
            return True
        return failure_kind in effective_kinds

    def get_targets(self) -> tuple[str, ...]:
        return self.fallback_step_names or self.fallback_actions


@dataclass
class ExecutionRequest:
    task_type: str
    user_request: str
    repo_root: str
    conversation_id: str | None = None
    session_id: str | None = None
    relative_path: str | None = None
    operations: list[dict[str, Any]] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionStep:
    name: str
    action: str | None = None
    handler: Callable[[Any], Any] | None = None
    enabled: bool = True
    retry_limit: int = 0
    stop_on_failure: bool = True
    rollback_on_failure: bool = False
    retry_policy: RetryPolicy | None = None
    retry: RetryPolicy | None = None
    fallback_policy: FallbackPolicy | None = None
    fallback: FallbackPolicy | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    step_id: str = field(default_factory=lambda: f"step_{uuid4().hex[:8]}")

    def __post_init__(self) -> None:
        if self.action is None:
            self.action = self.name
        if self.retry_policy is None and self.retry is not None:
            self.retry_policy = self.retry
        if self.fallback_policy is None and self.fallback is not None:
            self.fallback_policy = self.fallback


@dataclass
class ExecutionPlan:
    task_type: str
    steps: list[ExecutionStep]
    requires_session: bool = False
    requires_validation: bool = False
    allow_rollback: bool = False
    plan_id: str = field(default_factory=lambda: f"plan_{uuid4().hex[:8]}")


def _as_dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, Mapping):
        return dict(value)
    return {}


@dataclass
class StepResult:
    step_id: str = ""
    action: str = ""
    ok: bool | None = None
    status: ExecutionStatus = ExecutionStatus.SUCCESS
    summary: str | None = None
    updates: dict[str, Any] = field(default_factory=dict)
    output: Any = field(default_factory=dict)
    message: str | None = None
    error_code: str | None = None
    failure_kind: FailureKind = FailureKind.UNKNOWN
    payload: Any = field(default_factory=dict)
    retry_count: int = 0

    def __post_init__(self) -> None:
        if self.message is None:
            self.message = self.summary
        if self.summary is None:
            self.summary = self.message
        if self.ok is None:
            self.ok = self.status == ExecutionStatus.SUCCESS

        output_dict = _as_dict(self.output)
        payload_dict = _as_dict(self.payload)
        updates_dict = _as_dict(self.updates)

        merged: dict[str, Any] = {}
        if output_dict:
            merged.update(output_dict)
        if payload_dict:
            merged.update(payload_dict)
        if updates_dict:
            merged.update(updates_dict)

        if merged:
            self.output = dict(merged)
            self.payload = dict(merged)
            self.updates = dict(merged)
        else:
            if self.output is None:
                self.output = {}
            if self.payload is None:
                self.payload = {}
            self.updates = {}


@dataclass
class ExecutionContext:
    request: ExecutionRequest | None = None
    plan: ExecutionPlan | None = None
    session_id: str | None = None
    sandbox_path: str | None = None
    step_results: list[StepResult] = field(default_factory=list)
    current_step_index: int = 0
    status: ExecutionStatus = ExecutionStatus.PENDING
    state: dict[str, Any] = field(default_factory=lambda: {"edited_files": []})

    def __getitem__(self, key: str) -> Any:
        if key == "request":
            return self.request
        if key == "plan":
            return self.plan
        if key == "session_id":
            return self.session_id
        if key == "sandbox_path":
            return self.sandbox_path
        if key == "step_results":
            return self.step_results
        if key == "current_step_index":
            return self.current_step_index
        if key == "status":
            return self.status
        if key == "state":
            return self.state
        if key in self.state:
            return self.state[key]
        raise KeyError(key)

    def __setitem__(self, key: str, value: Any) -> None:
        if key == "request":
            self.request = value
        elif key == "plan":
            self.plan = value
        elif key == "session_id":
            self.session_id = value
            self.state["session_id"] = value
        elif key == "sandbox_path":
            self.sandbox_path = value
            self.state["sandbox_path"] = value
        elif key == "step_results":
            self.step_results = value
        elif key == "current_step_index":
            self.current_step_index = value
        elif key == "status":
            self.status = value
        elif key == "state":
            self.state = value
        else:
            self.state[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        try:
            return self[key]
        except KeyError:
            return default

    def add_step_result(self, result: StepResult) -> None:
        self.step_results.append(result)

        merged: dict[str, Any] = {}
        merged.update(_as_dict(result.output))
        merged.update(_as_dict(result.payload))
        merged.update(_as_dict(result.updates))

        if merged:
            self.state.update(merged)

        step_key = result.action or result.step_id
        if step_key:
            step_store: Any = result.output
            if not isinstance(step_store, Mapping):
                step_store = result.payload
            if not isinstance(step_store, Mapping):
                step_store = result.summary
            self.state[step_key] = step_store

        if self.session_id is None:
            self.session_id = self.state.get("session_id")
        if self.sandbox_path is None:
            self.sandbox_path = self.state.get("sandbox_path")


@dataclass
class ExecutionResult:
    ok: bool
    status: ExecutionStatus
    plan_id: str | None
    conversation_id: str | None
    session_id: str | None
    steps: list[StepResult]
    final_output: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    trace: list[dict[str, Any]] = field(default_factory=list)
    state: dict[str, Any] = field(default_factory=dict)
    failed_step: str | None = None
    stop_reason: str | None = None
    context: ExecutionContext | None = None


class PlannerProtocol(Protocol):
    def build_execution_plan(self, request: ExecutionRequest) -> ExecutionPlan: ...


class SessionServiceProtocol(Protocol):
    def create_task_session(self, repo_root: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]: ...


class EditOrchestratorProtocol(Protocol):
    def edit(self, context: ExecutionContext) -> dict[str, Any]: ...
    def preview_diff(self, context: ExecutionContext) -> dict[str, Any]: ...


class ValidationServiceProtocol(Protocol):
    def run_validation(self, context: ExecutionContext) -> dict[str, Any]: ...


class RollbackServiceProtocol(Protocol):
    def rollback_session(self, session_id: str) -> dict[str, Any]: ...


class AnalysisExecutorProtocol(Protocol):
    def analyze(self, context: ExecutionContext) -> dict[str, Any]: ...


class _DefaultPlanner:
    def build_execution_plan(self, request: ExecutionRequest) -> ExecutionPlan:
        if request.task_type == "analyze":
            return ExecutionPlan(
                task_type="analyze",
                steps=[
                    ExecutionStep(name="preview_plan", action="preview_plan"),
                    ExecutionStep(name="analyze", action="analyze"),
                ],
            )
        return ExecutionPlan(
            task_type=request.task_type or "edit",
            requires_session=True,
            requires_validation=True,
            allow_rollback=True,
            steps=[
                ExecutionStep(name="preview_plan", action="preview_plan"),
                ExecutionStep(name="create_session", action="create_session", retry_limit=1),
                ExecutionStep(name="edit", action="edit"),
                ExecutionStep(name="preview_diff", action="preview_diff"),
                ExecutionStep(name="validate", action="validate"),
            ],
        )


class _DefaultSessionService:
    def create_task_session(self, repo_root: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        return {
            "ok": True,
            "session_id": f"session_{uuid4().hex[:8]}",
            "sandbox_path": f"{repo_root}/agent_runtime/sandbox_workspaces/default",
            "repo_root": repo_root,
        }


class _DefaultEditOrchestrator:
    def edit(self, context: ExecutionContext) -> dict[str, Any]:
        return {"ok": True, "message": "預設 edit stub 成功"}

    def preview_diff(self, context: ExecutionContext) -> dict[str, Any]:
        return {"ok": True, "message": "預設 diff stub 成功", "diff_text": ""}


class _DefaultValidationService:
    def run_validation(self, context: ExecutionContext) -> dict[str, Any]:
        return {"ok": True, "message": "預設 validation stub 通過"}


class _DefaultRollbackService:
    def rollback_session(self, session_id: str) -> dict[str, Any]:
        return {"ok": True, "message": "預設 rollback stub 成功", "session_id": session_id}


class _DefaultAnalysisExecutor:
    def analyze(self, context: ExecutionContext) -> dict[str, Any]:
        return {"summary": "預設 analyze stub 成功", "files": []}


class ExecutionController:
    def __init__(
        self,
        name: str | None = None,
        planner: PlannerProtocol | None = None,
        session_service: SessionServiceProtocol | None = None,
        edit_orchestrator: EditOrchestratorProtocol | None = None,
        validation_service: ValidationServiceProtocol | None = None,
        rollback_service: RollbackServiceProtocol | None = None,
        analysis_executor: AnalysisExecutorProtocol | None = None,
    ) -> None:
        self.name = name or "execution_controller"
        self.planner = planner or _DefaultPlanner()
        self.session_service = session_service or _DefaultSessionService()
        self.edit_orchestrator = edit_orchestrator or _DefaultEditOrchestrator()
        self.validation_service = validation_service or _DefaultValidationService()
        self.rollback_service = rollback_service or _DefaultRollbackService()
        self.analysis_executor = analysis_executor or _DefaultAnalysisExecutor()
        self.trace: list[dict[str, Any]] = []
        self.state: dict[str, Any] = {
            "controller_name": self.name,
            "status": StepStatus.PENDING,
            "last_failure_kind": None,
            "retry_count": 0,
            "edited_files": [],
        }

    def _trace_status_value(self, status: StepStatus) -> str:
        if status in (StepStatus.ERROR, StepStatus.FAILED):
            return "error"
        return status.value

    def record_step(self, step_name: str, status: StepStatus, message: str | None = None) -> None:
        self.trace.append({"name": step_name, "status": self._trace_status_value(status), "message": message})
        self.state["status"] = status

    def record_fallback(self, from_step: str, to_step: str) -> None:
        self.trace.append({"name": from_step, "status": "fallback", "message": f"{from_step} -> {to_step}"})

    def run(
        self,
        request_or_steps: ExecutionRequest | list[ExecutionStep] | None = None,
        *,
        steps: list[ExecutionStep] | None = None,
        initial_state: dict[str, Any] | None = None,
    ) -> ExecutionResult:
        if steps is not None:
            return self._run_legacy_steps(steps, initial_state=initial_state)
        if isinstance(request_or_steps, list):
            return self._run_legacy_steps(request_or_steps, initial_state=initial_state)
        if request_or_steps is None:
            return self._run_legacy_steps([], initial_state=initial_state)

        request = request_or_steps
        plan = self.build_plan(request)
        context = ExecutionContext(request=request, plan=plan, session_id=request.session_id)
        if initial_state:
            context.state.update(initial_state)
            if context.session_id is None:
                context.session_id = context.state.get("session_id")
            if context.sandbox_path is None:
                context.sandbox_path = context.state.get("sandbox_path")
        return self.execute_plan(context)

    def _run_legacy_steps(self, steps: list[ExecutionStep], initial_state: dict[str, Any] | None = None) -> ExecutionResult:
        context = ExecutionContext()
        if initial_state:
            context.state.update(initial_state)
            context.session_id = context.state.get("session_id")
            context.sandbox_path = context.state.get("sandbox_path")

        step_lookup = {step.name: step for step in steps}

        for step in steps:
            if not step.enabled:
                continue

            result = self._execute_legacy_handler_step(context, step)
            context.add_step_result(result)
            self.record_step(step.name, result.status, result.summary)

            if result.ok:
                continue

            fallback_policy = step.fallback_policy or FallbackPolicy()
            if fallback_policy.can_fallback(result.failure_kind):
                targets = fallback_policy.get_targets()
                if targets:
                    target_name = targets[0]
                    target = step_lookup.get(target_name)
                    if target is not None and target.enabled:
                        self.record_fallback(step.name, target.name)
                        fallback_result = self._execute_legacy_handler_step(context, target)
                        context.add_step_result(fallback_result)
                        self.record_step(target.name, fallback_result.status, fallback_result.summary)
                        context.state["fallback_used"] = True

            return self._build_result(
                context=context,
                ok=False,
                status=StepStatus.STOPPED,
                error=result.summary,
                failed_step=step.name,
                stop_reason=result.failure_kind.value,
            )

        final_status = context.step_results[-1].status if context.step_results else StepStatus.SUCCESS
        return self._build_result(
            context=context,
            ok=True,
            status=final_status,
            failed_step=None,
            stop_reason=None,
        )

    def _execute_legacy_handler_step(self, context: ExecutionContext, step: ExecutionStep) -> StepResult:
        if step.handler is None:
            return StepResult(
                step_id=step.step_id,
                action=step.action or step.name,
                ok=False,
                status=StepStatus.ERROR,
                summary=f"step {step.name} 缺少 handler",
                failure_kind=FailureKind.NON_RETRYABLE,
            )

        attempt = 0
        while True:
            try:
                raw = step.handler(context)

                if isinstance(raw, StepResult):
                    if not raw.step_id:
                        raw.step_id = step.step_id
                    if not raw.action:
                        raw.action = step.action or step.name
                    raw.retry_count = attempt
                    return raw

                if isinstance(raw, dict):
                    status_raw = raw.get("status", "success")
                    status = StepStatus.SUCCESS if status_raw == "success" else StepStatus.ERROR
                    return StepResult(
                        step_id=step.step_id,
                        action=step.action or step.name,
                        ok=(status == StepStatus.SUCCESS),
                        status=status,
                        summary=raw.get("summary"),
                        updates=raw.get("updates", {}),
                        output=raw.get("output", {}),
                        failure_kind=raw.get("failure_kind", FailureKind.UNKNOWN),
                        retry_count=attempt,
                    )

                return StepResult(
                    step_id=step.step_id,
                    action=step.action or step.name,
                    ok=False,
                    status=StepStatus.ERROR,
                    summary="handler 回傳格式不支援",
                    failure_kind=FailureKind.NON_RETRYABLE,
                    retry_count=attempt,
                )

            except Exception as exc:
                retry_policy = step.retry_policy or RetryPolicy(max_attempts=step.retry_limit)
                if retry_policy.should_retry_exception(exc, attempt):
                    self.record_step(step.name, StepStatus.ERROR, str(exc))
                    attempt += 1
                    context.state["retry_count"] = attempt
                    continue
                raise

    def build_plan(self, request: ExecutionRequest) -> ExecutionPlan:
        return self.planner.build_execution_plan(request)

    def execute_plan(self, context: ExecutionContext) -> ExecutionResult:
        context.status = ExecutionStatus.RUNNING
        self.state["status"] = StepStatus.RUNNING

        for step in context.plan.steps or []:
            if not step.enabled:
                continue

            step_result = self._execute_step_with_retry(context, step)
            context.add_step_result(step_result)
            self.record_step(step.action or step.name, step_result.status, step_result.message)

            if step_result.status == ExecutionStatus.ROLLED_BACK:
                context.status = ExecutionStatus.ROLLED_BACK
                self.state["status"] = StepStatus.ROLLED_BACK
                return self._build_result(
                    context=context,
                    ok=False,
                    status=ExecutionStatus.ROLLED_BACK,
                    error=step_result.message or "流程已回滾",
                    failed_step=step.name,
                    stop_reason=FailureKind.VALIDATION.value,
                )

            if step_result.ok:
                continue

            if step.stop_on_failure:
                context.status = ExecutionStatus.STOPPED
                self.state["status"] = StepStatus.STOPPED
                return self._build_result(
                    context=context,
                    ok=False,
                    status=ExecutionStatus.STOPPED,
                    error=step_result.message or f"步驟失敗：{step.action}",
                    failed_step=step.name,
                    stop_reason=step_result.failure_kind.value,
                )

        context.status = ExecutionStatus.SUCCESS
        self.state["status"] = StepStatus.SUCCESS
        return self._build_result(
            context=context,
            ok=True,
            status=ExecutionStatus.SUCCESS,
            final_output=self._collect_final_output(context),
            failed_step=None,
            stop_reason=None,
        )

    def _execute_step_with_retry(self, context: ExecutionContext, step: ExecutionStep) -> StepResult:
        attempt = 0
        while True:
            result = self.execute_step(context, step, retry_count=attempt)

            if result.ok and result.status != ExecutionStatus.ROLLED_BACK:
                return result
            if result.status == ExecutionStatus.ROLLED_BACK:
                return result
            if self.should_retry(step, result, attempt):
                attempt += 1
                continue
            if self.should_rollback(context, step, result):
                return self._execute_rollback(context, reason=result.message or (step.action or step.name))
            return result

    def execute_step(self, context: ExecutionContext, step: ExecutionStep, retry_count: int = 0) -> StepResult:
        try:
            action = step.action or step.name

            if action == "preview_plan":
                return StepResult(
                    step_id=step.step_id,
                    action=action,
                    ok=True,
                    status=ExecutionStatus.SUCCESS,
                    summary="規劃完成",
                    output={"plan_id": context.plan.plan_id if context.plan else None},
                    retry_count=retry_count,
                )

            if action == "create_session":
                session = self.session_service.create_task_session(
                    repo_root=context.request.repo_root,
                    metadata=context.request.metadata if context.request else None,
                )
                context["session_id"] = session.get("session_id")
                context["sandbox_path"] = session.get("sandbox_path")
                return StepResult(
                    step_id=step.step_id,
                    action=action,
                    ok=bool(session.get("ok", True)),
                    status=ExecutionStatus.SUCCESS if session.get("ok", True) else ExecutionStatus.ERROR,
                    summary=session.get("message", "已建立 session"),
                    output=session,
                    failure_kind=FailureKind.SESSION_ERROR if not session.get("ok", True) else FailureKind.UNKNOWN,
                    retry_count=retry_count,
                )

            if action == "analyze":
                payload = self.analysis_executor.analyze(context)
                ok = payload.get("ok", True)
                return StepResult(
                    step_id=step.step_id,
                    action=action,
                    ok=ok,
                    status=ExecutionStatus.SUCCESS if ok else ExecutionStatus.ERROR,
                    summary=payload.get("message", "分析完成"),
                    output=payload,
                    failure_kind=FailureKind.TOOL_ERROR if not ok else FailureKind.UNKNOWN,
                    retry_count=retry_count,
                )

            if action == "edit":
                payload = self.edit_orchestrator.edit(context)
                ok = payload.get("ok", True)
                return StepResult(
                    step_id=step.step_id,
                    action=action,
                    ok=ok,
                    status=ExecutionStatus.SUCCESS if ok else ExecutionStatus.ERROR,
                    summary=payload.get("message", "編輯完成" if ok else "編輯失敗"),
                    error_code=payload.get("error_code"),
                    failure_kind=FailureKind.EDIT_ERROR if not ok else FailureKind.UNKNOWN,
                    output=payload,
                    retry_count=retry_count,
                )

            if action == "preview_diff":
                payload = self.edit_orchestrator.preview_diff(context)
                ok = payload.get("ok", True)
                return StepResult(
                    step_id=step.step_id,
                    action=action,
                    ok=ok,
                    status=ExecutionStatus.SUCCESS if ok else ExecutionStatus.ERROR,
                    summary=payload.get("message", "diff 產生完成" if ok else "diff 產生失敗"),
                    error_code=payload.get("error_code"),
                    failure_kind=FailureKind.DIFF_ERROR if not ok else FailureKind.UNKNOWN,
                    output=payload,
                    retry_count=retry_count,
                )

            if action == "validate":
                payload = self.validation_service.run_validation(context)
                ok = payload.get("ok", False)
                return StepResult(
                    step_id=step.step_id,
                    action=action,
                    ok=ok,
                    status=ExecutionStatus.SUCCESS if ok else ExecutionStatus.ERROR,
                    summary=payload.get("message", "驗證通過" if ok else "驗證失敗"),
                    error_code=payload.get("error_code"),
                    failure_kind=FailureKind.VALIDATION if not ok else FailureKind.UNKNOWN,
                    output=payload,
                    retry_count=retry_count,
                )

            if action == "rollback":
                return self._execute_rollback(context, reason="manual_step")

            return StepResult(
                step_id=step.step_id,
                action=action,
                ok=False,
                status=ExecutionStatus.ERROR,
                summary=f"未知 action：{action}",
                error_code="unknown_action",
                failure_kind=FailureKind.NON_RETRYABLE,
                retry_count=retry_count,
            )

        except Exception as exc:
            return StepResult(
                step_id=step.step_id,
                action=step.action or step.name,
                ok=False,
                status=ExecutionStatus.ERROR,
                summary=f"{step.action or step.name} 發生例外：{exc}",
                error_code="exception",
                failure_kind=self._infer_failure_kind(step.action or step.name),
                retry_count=retry_count,
            )

    def should_retry(self, step: ExecutionStep, step_result: StepResult, attempt: int) -> bool:
        policy = step.retry_policy or RetryPolicy(max_attempts=step.retry_limit)
        return policy.should_retry(step_result.failure_kind, attempt)

    def should_rollback(self, context: ExecutionContext, step: ExecutionStep, step_result: StepResult) -> bool:
        if not context.session_id:
            return False
        if (step.action or step.name) == "validate" and not step_result.ok:
            return True
        return step.rollback_on_failure and not step_result.ok

    def _infer_failure_kind(self, action: str) -> FailureKind:
        if action == "create_session":
            return FailureKind.SESSION_ERROR
        if action == "edit":
            return FailureKind.EDIT_ERROR
        if action == "preview_diff":
            return FailureKind.DIFF_ERROR
        if action == "validate":
            return FailureKind.VALIDATION
        if action == "rollback":
            return FailureKind.ROLLBACK_ERROR
        return FailureKind.UNKNOWN

    def _execute_rollback(self, context: ExecutionContext, reason: str) -> StepResult:
        if not context.session_id:
            return StepResult(
                step_id=f"step_{uuid4().hex[:8]}",
                action="rollback",
                ok=False,
                status=ExecutionStatus.HIGH_RISK_FAILURE,
                summary="需要 rollback，但缺少 session_id",
                error_code="missing_session_id",
                failure_kind=FailureKind.ROLLBACK_ERROR,
            )
        try:
            payload = self.rollback_service.rollback_session(context.session_id)
            ok = payload.get("ok", True)
            return StepResult(
                step_id=f"step_{uuid4().hex[:8]}",
                action="rollback",
                ok=ok,
                status=ExecutionStatus.ROLLED_BACK if ok else ExecutionStatus.HIGH_RISK_FAILURE,
                summary=payload.get("message", f"已回滾（原因：{reason}）" if ok else "回滾失敗"),
                error_code=payload.get("error_code"),
                failure_kind=FailureKind.ROLLBACK_ERROR if not ok else FailureKind.UNKNOWN,
                output=payload,
            )
        except Exception as exc:
            return StepResult(
                step_id=f"step_{uuid4().hex[:8]}",
                action="rollback",
                ok=False,
                status=ExecutionStatus.HIGH_RISK_FAILURE,
                summary=f"rollback 發生例外：{exc}",
                error_code="rollback_exception",
                failure_kind=FailureKind.ROLLBACK_ERROR,
            )

    def _collect_final_output(self, context: ExecutionContext) -> dict[str, Any]:
        return {
            "analysis": context.get("analyze"),
            "diff": context.get("preview_diff"),
            "validation": context.get("validate"),
            "summary": context.get("summary"),
        }

    def _build_result(
        self,
        context: ExecutionContext,
        ok: bool,
        status: ExecutionStatus,
        final_output: dict[str, Any] | None = None,
        error: str | None = None,
        failed_step: str | None = None,
        stop_reason: str | None = None,
    ) -> ExecutionResult:
        return ExecutionResult(
            ok=ok,
            status=status,
            plan_id=context.plan.plan_id if context.plan else None,
            conversation_id=context.request.conversation_id if context.request else None,
            session_id=context.session_id,
            steps=context.step_results,
            final_output=final_output or {},
            error=error,
            trace=list(self.trace),
            state=dict(context.state),
            failed_step=failed_step,
            stop_reason=stop_reason,
            context=context,
        )
