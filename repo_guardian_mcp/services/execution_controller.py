from __future__ import annotations

"""
ExecutionController.

兼容兩套 contract：
1. 新版正式 controller API
   - ExecutionStep(retry=..., stop=..., fallback=FallbackPolicy(...))
   - controller.run(steps, initial_state={...}) -> ExecutionSummary
2. 舊版 orchestrator API
   - ExecutionStep(max_retries=..., stop_on=..., fallback=<callable>)
   - controller.run(steps, initial_context={...}) -> ExecutionSummary

重點：
- trace 永遠不能反噬主流程
- state/context 同時可用
- 保持既有主線相容，再逐步往正式版收斂
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
import time
from typing import Any, Callable, Iterable, Mapping, MutableMapping


class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"
    SKIPPED = "skipped"
    STOPPED = "stopped"
    FALLBACK = "fallback"


class FailureKind(str, Enum):
    TRANSIENT = "transient"
    VALIDATION = "validation"
    USER_INPUT = "user_input"
    TOOLING = "tooling"
    INTERNAL = "internal"
    STOP = "stop"


@dataclass(slots=True)
class RetryPolicy:
    max_attempts: int = 1
    backoff_seconds: float = 0.0
    retry_on_kinds: tuple[FailureKind, ...] = (FailureKind.TRANSIENT, FailureKind.TOOLING)
    retry_on_exceptions: tuple[type[BaseException], ...] = ()

    def should_retry(self, *, attempt: int, error: BaseException | None, failure_kind: FailureKind) -> bool:
        if attempt >= self.max_attempts:
            return False
        if failure_kind in self.retry_on_kinds:
            return True
        if error is None:
            return False
        return bool(self.retry_on_exceptions and isinstance(error, self.retry_on_exceptions))


@dataclass(slots=True)
class StopPolicy:
    stop_on_kinds: tuple[FailureKind, ...] = (
        FailureKind.VALIDATION,
        FailureKind.USER_INPUT,
        FailureKind.INTERNAL,
        FailureKind.STOP,
    )
    stop_on_exceptions: tuple[type[BaseException], ...] = ()

    def should_stop(self, *, error: BaseException | None, failure_kind: FailureKind) -> bool:
        if failure_kind in self.stop_on_kinds:
            return True
        if error is None:
            return False
        return bool(self.stop_on_exceptions and isinstance(error, self.stop_on_exceptions))


@dataclass(slots=True)
class FallbackPolicy:
    enabled: bool = False
    fallback_step_names: tuple[str, ...] = ()
    activate_on_kinds: tuple[FailureKind, ...] = (FailureKind.TOOLING, FailureKind.TRANSIENT)

    def should_activate(self, failure_kind: FailureKind) -> bool:
        return self.enabled and failure_kind in self.activate_on_kinds and bool(self.fallback_step_names)


@dataclass(slots=True)
class StepResult:
    status: StepStatus
    output: Any = None
    summary: str | None = None
    updates: Mapping[str, Any] | None = None
    failure_kind: FailureKind | None = None
    metadata: Mapping[str, Any] | None = None


@dataclass(slots=True)
class StepContext:
    state: MutableMapping[str, Any]
    trace: list[dict[str, Any]]
    controller_name: str
    started_at: str

    @property
    def context(self) -> MutableMapping[str, Any]:
        return self.state

    # legacy mapping compatibility
    def get(self, key: str, default: Any = None) -> Any:
        return self.state.get(key, default)

    def __getitem__(self, key: str) -> Any:
        return self.state[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.state[key] = value

    def __contains__(self, key: object) -> bool:
        return key in self.state

    def update(self, *args: Any, **kwargs: Any) -> None:
        self.state.update(*args, **kwargs)

    def keys(self):
        return self.state.keys()

    def values(self):
        return self.state.values()

    def items(self):
        return self.state.items()


StepHandler = Callable[[StepContext | MutableMapping[str, Any]], StepResult | Mapping[str, Any] | Any]
LegacyFallback = Callable[[BaseException, MutableMapping[str, Any]], Any]


@dataclass(init=False)
class ExecutionStep:
    name: str
    handler: StepHandler
    retry: RetryPolicy
    stop: StopPolicy
    fallback: FallbackPolicy | None
    description: str | None
    tags: tuple[str, ...]
    enabled: bool

    # legacy compatibility
    max_retries: int
    stop_on: tuple[type[BaseException], ...]
    fallback_handler: LegacyFallback | None

    def __init__(
        self,
        name: str,
        handler: StepHandler,
        retry: RetryPolicy | None = None,
        stop: StopPolicy | None = None,
        fallback: FallbackPolicy | LegacyFallback | None = None,
        description: str | None = None,
        tags: tuple[str, ...] = (),
        enabled: bool = True,
        *,
        max_retries: int = 0,
        stop_on: type[BaseException] | tuple[type[BaseException], ...] | None = None,
    ) -> None:
        self.name = name
        self.handler = handler
        self.description = description
        self.tags = tags
        self.enabled = enabled
        self.max_retries = max_retries

        if stop_on is None:
            self.stop_on = ()
        elif isinstance(stop_on, tuple):
            self.stop_on = stop_on
        else:
            self.stop_on = (stop_on,)

        if retry is None:
            retry_attempts = max(1, max_retries + 1)
            retry = RetryPolicy(
                max_attempts=retry_attempts,
                retry_on_kinds=(FailureKind.TRANSIENT, FailureKind.TOOLING),
                retry_on_exceptions=(),
            )
        self.retry = retry

        if stop is None:
            stop = StopPolicy(stop_on_exceptions=self.stop_on)
        self.stop = stop

        self.fallback_handler = fallback if callable(fallback) else None
        self.fallback = fallback if isinstance(fallback, FallbackPolicy) else None


@dataclass(slots=True)
class ExecutionSummary:
    ok: bool
    status: StepStatus
    state: dict[str, Any]
    trace: list[dict[str, Any]]
    error: str | None = None
    failed_step: str | None = None
    stop_reason: str | None = None

    @property
    def context(self) -> dict[str, Any]:
        return self.state

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "status": self.status.value,
            "state": self.state,
            "context": self.state,
            "trace": self.trace,
            "error": self.error,
            "failed_step": self.failed_step,
            "stop_reason": self.stop_reason,
        }


ExecutionResult = ExecutionSummary


class ExecutionController:
    def __init__(self, *, name: str = "execution_controller") -> None:
        self.name = name

    def run(
        self,
        steps: Iterable[ExecutionStep],
        *,
        initial_state: Mapping[str, Any] | None = None,
        initial_context: Mapping[str, Any] | None = None,
    ) -> ExecutionSummary:
        if initial_state is not None and initial_context is not None:
            raise TypeError("只能提供 initial_state 或 initial_context 其中一個")

        state: dict[str, Any] = dict(initial_state if initial_state is not None else (initial_context or {}))
        trace: list[dict[str, Any]] = []
        started_at = self._now_iso()
        context = StepContext(state=state, trace=trace, controller_name=self.name, started_at=started_at)

        step_map = {step.name: step for step in steps}
        queue = [step.name for step in step_map.values() if step.enabled]
        index = 0

        while index < len(queue):
            step = step_map[queue[index]]
            index += 1

            result = self._run_step(step=step, context=context)
            if result["state_updates"]:
                state.update(result["state_updates"])

            if result["status"] == StepStatus.SUCCESS:
                continue

            failure_kind = result["failure_kind"] or FailureKind.INTERNAL
            error = result["error"]

            if step.fallback_handler is not None and error is not None:
                try:
                    fallback_output = step.fallback_handler(error, state)
                    state[step.name] = fallback_output
                    self._push_trace(
                        trace,
                        name=f"{step.name}:fallback",
                        status=StepStatus.SUCCESS.value,
                        attempt=1,
                        result=fallback_output,
                    )
                    continue
                except Exception as fallback_exc:  # noqa: BLE001
                    self._push_trace(
                        trace,
                        name=f"{step.name}:fallback",
                        status=StepStatus.ERROR.value,
                        attempt=1,
                        error=str(fallback_exc),
                    )
                    return ExecutionSummary(
                        ok=False,
                        status=StepStatus.ERROR,
                        state=dict(state),
                        trace=trace,
                        error=str(fallback_exc),
                        failed_step=f"{step.name}:fallback",
                        stop_reason=failure_kind.value,
                    )

            if step.fallback and step.fallback.should_activate(failure_kind):
                fallback_names = [name for name in step.fallback.fallback_step_names if name in step_map]
                if fallback_names:
                    queue[index:index] = fallback_names
                    self._push_trace(
                        trace,
                        name=step.name,
                        status=StepStatus.FALLBACK.value,
                        attempt=result["attempt"],
                        error=str(error) if error else None,
                        summary=f"啟用 fallback: {', '.join(fallback_names)}",
                    )

            if step.stop.should_stop(error=error, failure_kind=failure_kind):
                return ExecutionSummary(
                    ok=False,
                    status=StepStatus.STOPPED,
                    state=dict(state),
                    trace=trace,
                    error=str(error) if error else result.get("summary") or "執行已停止",
                    failed_step=step.name,
                    stop_reason=failure_kind.value,
                )

            return ExecutionSummary(
                ok=False,
                status=StepStatus.ERROR,
                state=dict(state),
                trace=trace,
                error=str(error) if error else result.get("summary") or "執行失敗",
                failed_step=step.name,
                stop_reason=failure_kind.value,
            )

        return ExecutionSummary(
            ok=True,
            status=StepStatus.SUCCESS,
            state=dict(state),
            trace=trace,
            error=None,
            failed_step=None,
            stop_reason=None,
        )

    def _run_step(self, *, step: ExecutionStep, context: StepContext) -> dict[str, Any]:
        attempt = 0
        while True:
            attempt += 1
            started = time.perf_counter()
            error: BaseException | None = None
            failure_kind: FailureKind | None = None
            state_updates: dict[str, Any] = {}
            summary: str | None = None
            output: Any = None
            metadata: Mapping[str, Any] | None = None
            status = StepStatus.RUNNING

            try:
                try:
                    raw = step.handler(context)
                except TypeError:
                    raw = step.handler(context.state)
                normalized = self._normalize_result(raw)
                status = normalized.status
                output = normalized.output
                summary = normalized.summary
                metadata = normalized.metadata
                if normalized.updates:
                    state_updates.update(dict(normalized.updates))
                if output is not None:
                    context.state[step.name] = output
                failure_kind = normalized.failure_kind
                if status == StepStatus.ERROR and failure_kind is None:
                    failure_kind = FailureKind.INTERNAL
            except Exception as exc:  # noqa: BLE001
                error = exc
                status = StepStatus.ERROR
                summary = str(exc)
                failure_kind = self._classify_exception(exc)

            duration_ms = round((time.perf_counter() - started) * 1000, 2)
            self._push_trace(
                context.trace,
                name=step.name,
                status=status.value,
                attempt=attempt,
                result=output,
                error=str(error) if error else None,
                summary=summary,
                failure_kind=failure_kind.value if failure_kind else None,
                duration_ms=duration_ms,
                metadata=metadata,
                tags=list(step.tags),
            )

            if status == StepStatus.SUCCESS:
                return {
                    "status": status,
                    "attempt": attempt,
                    "output": output,
                    "summary": summary,
                    "metadata": metadata,
                    "failure_kind": None,
                    "state_updates": state_updates,
                    "error": None,
                }

            if step.retry.should_retry(
                attempt=attempt,
                error=error,
                failure_kind=failure_kind or FailureKind.INTERNAL,
            ):
                if step.retry.backoff_seconds > 0:
                    time.sleep(step.retry.backoff_seconds)
                continue

            return {
                "status": status,
                "attempt": attempt,
                "output": output,
                "summary": summary,
                "metadata": metadata,
                "failure_kind": failure_kind,
                "state_updates": state_updates,
                "error": error,
            }

    def _normalize_result(self, raw: StepResult | Mapping[str, Any] | Any) -> StepResult:
        if isinstance(raw, StepResult):
            return raw

        if isinstance(raw, Mapping):
            # 舊主線常直接回傳工具結果 dict，裡面的 status 可能是 workspace_ready / validation_passed 等
            # 這些不是 step status，不能直接拿來轉成 StepStatus。
            raw_status = raw.get("status")
            step_status = self._coerce_step_status(raw_status)

            raw_ok = raw.get("ok")
            if step_status is None:
                if raw_ok is False:
                    step_status = StepStatus.ERROR
                else:
                    step_status = StepStatus.SUCCESS

            failure_kind_value = raw.get("failure_kind")
            failure_kind = None
            if failure_kind_value is not None:
                try:
                    failure_kind = (
                        failure_kind_value
                        if isinstance(failure_kind_value, FailureKind)
                        else FailureKind(str(failure_kind_value))
                    )
                except ValueError:
                    failure_kind = None

            summary = raw.get("summary")
            if summary is None and raw_ok is False:
                summary = str(raw.get("error") or "執行失敗")

            output: Any
            if "output" in raw or "result" in raw:
                output = raw.get("output", raw.get("result"))
            else:
                output = dict(raw)

            metadata = raw.get("metadata")
            if metadata is None and raw_status is not None and step_status == StepStatus.SUCCESS:
                if not isinstance(raw_status, StepStatus):
                    metadata = {"legacy_status": raw_status}

            return StepResult(
                status=step_status,
                output=output,
                summary=summary,
                updates=raw.get("updates") or raw.get("state_updates"),
                failure_kind=failure_kind,
                metadata=metadata,
            )

        return StepResult(status=StepStatus.SUCCESS, output=raw)

    def _coerce_step_status(self, value: Any) -> StepStatus | None:
        if isinstance(value, StepStatus):
            return value
        if value is None:
            return None
        text = str(value).strip().lower()
        allowed = {status.value: status for status in StepStatus}
        return allowed.get(text)

    def _classify_exception(self, exc: BaseException) -> FailureKind:
        name = exc.__class__.__name__.lower()
        message = str(exc).lower()
        if "validation" in name or "validation" in message:
            return FailureKind.VALIDATION
        if "timeout" in name or "tempor" in message or "retry" in message:
            return FailureKind.TRANSIENT
        if isinstance(exc, (ValueError, FileNotFoundError)):
            return FailureKind.USER_INPUT
        return FailureKind.TOOLING

    def _push_trace(self, trace: list[dict[str, Any]], **payload: Any) -> None:
        try:
            trace.append({key: self._safe_trace_value(value) for key, value in payload.items()})
        except Exception as exc:  # noqa: BLE001
            trace.append(
                {
                    "name": str(payload.get("name", "unknown")),
                    "status": str(payload.get("status", StepStatus.ERROR.value)),
                    "attempt": int(payload.get("attempt", 1) or 1),
                    "result": repr(payload.get("result")),
                    "error": f"trace_serialize_error: {exc}",
                }
            )

    def _safe_trace_value(self, value: Any) -> Any:
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, Enum):
            return value.value
        from collections.abc import Mapping as abcMapping
        if isinstance(value, abcMapping):
            return {str(key): self._safe_trace_value(item) for key, item in value.items()}
        from collections.abc import Iterable as abcIterable
        if isinstance(value, (list, tuple, set)):
            return [self._safe_trace_value(item) for item in value]
        to_dict = getattr(value, "to_dict", None)
        if callable(to_dict):
            return self._safe_trace_value(to_dict())
        return repr(value)

    def _now_iso(self) -> str:
        return datetime.now(UTC).isoformat()