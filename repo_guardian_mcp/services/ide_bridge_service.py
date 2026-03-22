from __future__ import annotations

import json
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from repo_guardian_mcp.services.cli_agent_service import CLIAgentService
from repo_guardian_mcp.services.error_diagnosis_service import ErrorDiagnosisService
from repo_guardian_mcp.services.session_lifecycle_contract_service import SessionLifecycleContractService


class IDEBridgeService:
    """Local bridge for IDE integrations without remote dependencies."""

    def __init__(self, agent_service: CLIAgentService | None = None) -> None:
        self.agent_service = agent_service or CLIAgentService()
        self.lifecycle = SessionLifecycleContractService()
        self.diagnosis = ErrorDiagnosisService()

    def _tasks_dir(self, repo_root: str) -> Path:
        path = (Path(repo_root).resolve() / "agent_runtime" / "ide_bridge" / "tasks").resolve()
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _task_file(self, repo_root: str, task_id: str) -> Path:
        return self._tasks_dir(repo_root) / f"{task_id}.json"

    def _events_file(self, repo_root: str, task_id: str) -> Path:
        return self._tasks_dir(repo_root) / f"{task_id}.events.jsonl"

    def _write_task(self, repo_root: str, payload: dict[str, Any]) -> None:
        task_id = str(payload["task_id"])
        self._task_file(repo_root, task_id).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _read_task(self, repo_root: str, task_id: str) -> dict[str, Any] | None:
        path = self._task_file(repo_root, task_id)
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def _next_event_seq(self, repo_root: str, task_id: str) -> int:
        path = self._events_file(repo_root, task_id)
        if not path.exists():
            return 1
        count = 0
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    count += 1
        return count + 1

    def _append_event(
        self,
        repo_root: str,
        task_id: str,
        event: str,
        payload: dict[str, Any] | None = None,
        *,
        level: str = "info",
    ) -> None:
        row = {
            "seq": self._next_event_seq(repo_root, task_id),
            "timestamp_ms": int(time.time() * 1000),
            "event": event,
            "level": level,
            "payload": dict(payload or {}),
        }
        with self._events_file(repo_root, task_id).open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    def invoke(
        self,
        *,
        repo_root: str,
        prompt: str,
        task_type: str = "auto",
        session_id: str | None = None,
        plan_only: bool = False,
    ) -> dict[str, Any]:
        task_id = f"bridge-{int(time.time() * 1000)}-{uuid.uuid4().hex[:8]}"
        started_at_ms = int(time.time() * 1000)
        initial = {
            "ok": True,
            "protocol_version": "v1.local",
            "task_id": task_id,
            "plan_only": plan_only,
            "prompt": prompt,
            "task_type": task_type,
            "session_id": session_id,
            "bridge_status": "running",
            "started_at_ms": started_at_ms,
            "result": None,
        }
        self._write_task(repo_root, initial)
        self._append_event(
            repo_root,
            task_id,
            "submitted",
            {"prompt": prompt, "task_type": task_type, "plan_only": bool(plan_only)},
            level="info",
        )
        self._append_event(repo_root, task_id, "execution_started", {}, level="info")
        try:
            ctx = self.agent_service.build_context(
                repo_root=repo_root,
                user_request=prompt,
                task_type=task_type,
                session_id=session_id,
                metadata={"task_id": task_id, "source": "ide_bridge"},
            )
            result = self.agent_service.create_plan(ctx) if plan_only else self.agent_service.run(ctx)
            ok = bool(result.get("ok"))
            bridge_status = "completed" if ok else "failed"
            diagnosis = None
            if not ok:
                err = result.get("error")
                if isinstance(err, dict):
                    err_message = str(err.get("message") or err)
                else:
                    err_message = str(err or "")
                diagnosis = self.diagnosis.build_error_block(error=err_message, payload=result)
            output = {
                "ok": ok,
                "protocol_version": "v1.local",
                "task_id": task_id,
                "plan_only": plan_only,
                "prompt": prompt,
                "task_type": task_type,
                "session_id": result.get("session_id") or session_id,
                "bridge_status": bridge_status,
                "started_at_ms": started_at_ms,
                "finished_at_ms": int(time.time() * 1000),
                "latency_ms": int(time.time() * 1000) - started_at_ms,
                "diagnosis": diagnosis,
                "result": result,
            }
        except Exception as exc:  # noqa: BLE001
            diagnosis = self.diagnosis.build_error_block(error=str(exc), payload=None)
            output = {
                "ok": False,
                "protocol_version": "v1.local",
                "task_id": task_id,
                "plan_only": plan_only,
                "prompt": prompt,
                "task_type": task_type,
                "session_id": session_id,
                "bridge_status": "failed",
                "started_at_ms": started_at_ms,
                "finished_at_ms": int(time.time() * 1000),
                "latency_ms": int(time.time() * 1000) - started_at_ms,
                "diagnosis": diagnosis,
                "result": {"ok": False, "error": {"code": "execution_error", "message": str(exc)}},
            }
            self._append_event(
                repo_root,
                task_id,
                "execution_failed",
                {"error": str(exc), "diagnosis": diagnosis},
                level="error",
            )
        self._write_task(repo_root, output)
        self._append_event(
            repo_root,
            task_id,
            "completed",
            {
                "ok": output["ok"],
                "bridge_status": output.get("bridge_status"),
                "task_state": ((output.get("result") or {}).get("task_state") or "unknown"),
                "selected_skill": (output.get("result") or {}).get("selected_skill"),
                "latency_ms": output.get("latency_ms"),
                "diagnosis_code": ((output.get("diagnosis") or {}).get("code") if isinstance(output.get("diagnosis"), dict) else None),
            },
            level=("info" if output["ok"] else "error"),
        )
        return output

    def status(self, *, repo_root: str, task_id: str) -> dict[str, Any]:
        data = self._read_task(repo_root, task_id)
        if data is None:
            return {"ok": False, "error": f"task '{task_id}' not found"}
        self._append_event(repo_root, task_id, "status_checked", {})
        return {
            "ok": True,
            "protocol_version": "v1.local",
            "task_id": task_id,
            "status": data.get("bridge_status") or "unknown",
            "result": data.get("result"),
            "session_id": data.get("session_id"),
            "latency_ms": data.get("latency_ms"),
            "diagnosis": data.get("diagnosis"),
        }

    def trace(self, *, repo_root: str, task_id: str) -> dict[str, Any]:
        data = self._read_task(repo_root, task_id)
        if data is None:
            return {"ok": False, "error": f"task '{task_id}' not found"}
        self._append_event(repo_root, task_id, "trace_checked", {})
        result = dict(data.get("result") or {})
        return {
            "ok": True,
            "protocol_version": "v1.local",
            "task_id": task_id,
            "trace_summary": result.get("trace_summary"),
            "trace_summary_text": result.get("trace_summary_text"),
            "standardized_trace": result.get("standardized_trace"),
        }

    def events(self, *, repo_root: str, task_id: str, limit: int = 50) -> dict[str, Any]:
        path = self._events_file(repo_root, task_id)
        if not path.exists():
            return {"ok": False, "error": f"events for task '{task_id}' not found"}
        rows: list[dict[str, Any]] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except Exception:
                continue
        if limit > 0:
            rows = rows[-limit:]
        return {
            "ok": True,
            "protocol_version": "v1.local",
            "task_id": task_id,
            "count": len(rows),
            "events": rows,
        }

    def diagnose(self, *, repo_root: str, task_id: str) -> dict[str, Any]:
        data = self._read_task(repo_root, task_id)
        if data is None:
            return {"ok": False, "error": f"task '{task_id}' not found"}
        self._append_event(repo_root, task_id, "diagnosis_checked", {}, level="info")
        result = dict(data.get("result") or {})
        diagnosis = data.get("diagnosis")
        if not diagnosis:
            err = result.get("error")
            err_message = ""
            if isinstance(err, dict):
                err_message = str(err.get("message") or "")
            elif err:
                err_message = str(err)
            diagnosis = self.diagnosis.build_error_block(error=err_message, payload=result)
        recommended_next_commands = self._recommended_next_commands(
            repo_root=repo_root,
            task_id=task_id,
            bridge_status=str(data.get("bridge_status") or "unknown"),
            task_state=str(result.get("task_state") or "unknown"),
            selected_skill=str(result.get("selected_skill") or ""),
            session_id=(result.get("session_id") or data.get("session_id")),
            has_diagnosis=bool(diagnosis),
        )
        plain_summary, next_say_examples = self._plain_language_guidance(
            bridge_status=str(data.get("bridge_status") or "unknown"),
            task_state=str(result.get("task_state") or "unknown"),
            selected_skill=str(result.get("selected_skill") or ""),
            has_diagnosis=bool(diagnosis),
        )
        return {
            "ok": True,
            "protocol_version": "v1.local",
            "task_id": task_id,
            "bridge_status": data.get("bridge_status") or "unknown",
            "diagnosis": diagnosis,
            "task_state": result.get("task_state"),
            "selected_skill": result.get("selected_skill"),
            "trace_ref": result.get("trace_ref"),
            "latency_ms": data.get("latency_ms"),
            "plain_summary": plain_summary,
            "next_say_examples": next_say_examples,
            "recommended_next_commands": recommended_next_commands,
        }

    def _recommended_next_commands(
        self,
        *,
        repo_root: str,
        task_id: str,
        bridge_status: str,
        task_state: str,
        selected_skill: str,
        session_id: str | None,
        has_diagnosis: bool,
    ) -> list[str]:
        commands: list[str] = [
            f'uv run repo-guardian bridge status "{repo_root}" {task_id}',
            f'uv run repo-guardian bridge trace "{repo_root}" {task_id}',
        ]
        if session_id:
            commands.append(f'uv run repo-guardian bridge diff "{repo_root}" {session_id}')
        if has_diagnosis:
            commands.append(f'uv run repo-guardian bridge diagnose "{repo_root}" {task_id}')
        if bridge_status == "failed":
            if session_id:
                commands.append(f'uv run repo-guardian bridge rollback "{repo_root}" {session_id}')
            commands.append(
                f'uv run repo-guardian run "{repo_root}" --prompt "請先幫我分析剛剛失敗原因，先不要修改檔案" --task-type analyze'
            )
            return commands

        if bridge_status == "completed":
            if task_state == "validated" and selected_skill == "analyze_repo":
                commands.append(
                    f'uv run repo-guardian run "{repo_root}" --prompt "根據剛剛分析，請開始幫我修改並完成驗證" --task-type auto'
                )
            elif task_state == "validated" and selected_skill == "safe_edit":
                if session_id:
                    commands.append(f'uv run repo-guardian rollback "{repo_root}" {session_id}')
                commands.append(f'uv run repo-guardian health report "{repo_root}"')
            else:
                commands.append(f'uv run repo-guardian bridge queue "{repo_root}" --limit 20')
            return commands

        commands.append(f'uv run repo-guardian bridge queue "{repo_root}" --limit 20')
        return commands

    def _plain_language_guidance(
        self,
        *,
        bridge_status: str,
        task_state: str,
        selected_skill: str,
        has_diagnosis: bool,
    ) -> tuple[str, list[str]]:
        if bridge_status == "failed":
            return (
                "這次任務失敗了，但已經留下診斷資料。",
                [
                    "請幫我用白話文說明這次失敗原因，先不要改檔案。",
                    "請告訴我你下一步會怎麼修，列 3 個步驟。",
                ],
            )
        if bridge_status == "completed":
            if task_state == "validated" and selected_skill == "analyze_repo":
                return (
                    "分析已完成，還沒有開始改檔案。",
                    [
                        "根據剛剛分析，請開始修改並自動驗證。",
                        "先列出要改哪些檔案，再開始動手。",
                    ],
                )
            if task_state == "validated" and selected_skill == "safe_edit":
                return (
                    "修改與驗證都完成了。",
                    [
                        "請用白話文總結這次改了什麼。",
                        "如果我想回復，請幫我執行 rollback。",
                    ],
                )

        fallback = "任務狀態已更新，可以先看診斷與事件再決定下一步。" if has_diagnosis else "任務狀態已更新，可以繼續下一步。"
        return (
            fallback,
            [
                "請先幫我整理目前狀態，用白話文說明。",
                "請告訴我下一步最建議做什麼。",
            ],
        )

    def diff(self, *, repo_root: str, session_id: str) -> dict[str, Any]:
        return self.lifecycle.diff(repo_root=repo_root, session_id=session_id)

    def rollback(self, *, repo_root: str, session_id: str) -> dict[str, Any]:
        return self.lifecycle.rollback(repo_root=repo_root, session_id=session_id, keep_workspace=False)

    def list_tasks(self, *, repo_root: str, limit: int = 20) -> dict[str, Any]:
        tasks_dir = self._tasks_dir(repo_root)
        rows: list[dict[str, Any]] = []
        for path in sorted(tasks_dir.glob("bridge-*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            result = dict(data.get("result") or {})
            rows.append(
                {
                    "task_id": data.get("task_id"),
                    "prompt": data.get("prompt"),
                    "task_type": data.get("task_type"),
                    "plan_only": bool(data.get("plan_only")),
                    "ok": bool(data.get("ok")),
                    "bridge_status": data.get("bridge_status") or ("completed" if data.get("ok") else "failed"),
                    "task_state": result.get("task_state"),
                    "selected_skill": result.get("selected_skill"),
                    "session_id": data.get("session_id"),
                    "latency_ms": data.get("latency_ms"),
                    "diagnosis_code": ((data.get("diagnosis") or {}).get("code") if isinstance(data.get("diagnosis"), dict) else None),
                    "updated_at_ms": int(path.stat().st_mtime * 1000),
                }
            )
        if limit > 0:
            rows = rows[:limit]
        return {
            "ok": True,
            "protocol_version": "v1.local",
            "count": len(rows),
            "tasks": rows,
        }

    def queue(self, *, repo_root: str, limit: int = 50) -> dict[str, Any]:
        listed = self.list_tasks(repo_root=repo_root, limit=limit)
        tasks = list(listed.get("tasks") or [])
        counts = {"pending": 0, "running": 0, "completed": 0, "failed": 0, "unknown": 0}
        diagnosis_counts: dict[str, int] = {}
        for item in tasks:
            status = str(item.get("bridge_status") or "unknown")
            if status not in counts:
                status = "unknown"
            counts[status] += 1
            code = str(item.get("diagnosis_code") or "")
            if code:
                diagnosis_counts[code] = diagnosis_counts.get(code, 0) + 1
        return {
            "ok": True,
            "protocol_version": "v1.local",
            "count": len(tasks),
            "counts": counts,
            "diagnosis_counts": diagnosis_counts,
            "tasks": tasks,
        }

    def latest(self, *, repo_root: str) -> dict[str, Any]:
        listed = self.list_tasks(repo_root=repo_root, limit=1)
        tasks = listed.get("tasks") or []
        if not tasks:
            return {"ok": False, "error": "no bridge task found"}
        latest_task = tasks[0]
        task_id = str(latest_task.get("task_id"))
        status = self.status(repo_root=repo_root, task_id=task_id)
        trace = self.trace(repo_root=repo_root, task_id=task_id)
        events = self.events(repo_root=repo_root, task_id=task_id, limit=20)
        diagnosis = self.diagnose(repo_root=repo_root, task_id=task_id)
        return {
            "ok": True,
            "protocol_version": "v1.local",
            "latest_task": latest_task,
            "status": status,
            "trace": trace,
            "events": events,
            "diagnosis": diagnosis,
        }

    def cleanup(self, *, repo_root: str, days: int = 7, keep: int = 200, dry_run: bool = False) -> dict[str, Any]:
        tasks_dir = self._tasks_dir(repo_root)
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(days=max(0, days))

        task_files = sorted(tasks_dir.glob("bridge-*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        protected: set[Path] = set(task_files[: max(0, keep)])
        delete_targets: list[Path] = []

        for task_file in task_files:
            if task_file in protected:
                continue
            try:
                mtime = datetime.fromtimestamp(task_file.stat().st_mtime, tz=timezone.utc)
            except OSError:
                continue
            if mtime > cutoff:
                continue
            delete_targets.append(task_file)
            events_file = task_file.with_suffix(".events.jsonl")
            if events_file.exists():
                delete_targets.append(events_file)

        deleted: list[str] = []
        reclaimed_bytes = 0
        for path in delete_targets:
            try:
                size = path.stat().st_size
            except OSError:
                size = 0
            if not dry_run:
                try:
                    path.unlink(missing_ok=True)
                except OSError:
                    continue
            reclaimed_bytes += size
            deleted.append(path.name)

        return {
            "ok": True,
            "protocol_version": "v1.local",
            "dry_run": dry_run,
            "days": days,
            "keep": keep,
            "deleted_count": len(deleted),
            "reclaimed_bytes": reclaimed_bytes,
            "deleted_files": deleted,
        }
