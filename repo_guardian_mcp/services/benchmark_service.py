from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from repo_guardian_mcp.services.routing_observability_service import RoutingObservabilityService
from repo_guardian_mcp.services.task_orchestrator import TaskOrchestrator

DEFAULT_CORPUS_VERSION = "1.0"
DEFAULT_CORPUS_FILE = "corpus.v1.json"
DEFAULT_BENCHMARK_TARGET = "README.md"


def _build_default_benchmark_corpus() -> dict[str, Any]:
    return {
        "version": DEFAULT_CORPUS_VERSION,
        "name": "core-zh-tw-local-agent",
        "description": "本地端 coding agent 基準任務集（偏重新手白話輸入與主線流程穩定性）。",
        "updated_at": int(time.time() * 1000),
        "tasks": [
            {
                "name": "analyze_repo_structure_zh",
                "task_type": "analyze",
                "user_request": "請用白話文分析這個專案在做什麼，先不要改檔。",
            },
            {
                "name": "auto_status_zh",
                "task_type": "auto",
                "user_request": "幫我看看目前專案大概狀態，重點講就好。",
            },
            {
                "name": "auto_entrypoints_zh",
                "task_type": "auto",
                "user_request": "幫我找這個 repo 的主要入口點在哪裡。",
            },
            {
                "name": "edit_runtime_target_append",
                "task_type": "edit",
                "relative_path": DEFAULT_BENCHMARK_TARGET,
                "mode": "append",
                "content": "\nbenchmark keepalive line",
            },
            {
                "name": "overview_english",
                "task_type": "auto",
                "user_request": "show project overview in short",
            },
            {
                "name": "analyze_english",
                "task_type": "analyze",
                "user_request": "analyze repository structure",
            },
        ],
    }


class BenchmarkService:
    def __init__(
        self,
        *,
        orchestrator: TaskOrchestrator | None = None,
        observability: RoutingObservabilityService | None = None,
    ) -> None:
        self._orchestrator = orchestrator or TaskOrchestrator()
        self._observability = observability or RoutingObservabilityService()

    def _bench_dir(self, repo_root: str) -> Path:
        path = Path(repo_root).resolve() / "agent_runtime" / "benchmarks"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _tasks_file(self, repo_root: str) -> Path:
        return self._bench_dir(repo_root) / DEFAULT_CORPUS_FILE

    def _legacy_tasks_file(self, repo_root: str) -> Path:
        return self._bench_dir(repo_root) / "fixed_tasks.json"

    def _reports_dir(self, repo_root: str) -> Path:
        path = self._bench_dir(repo_root) / "reports"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _ensure_benchmark_target(self, repo_root: str) -> str:
        target = Path(repo_root).resolve() / DEFAULT_BENCHMARK_TARGET
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            target.write_text("# benchmark target\n", encoding="utf-8")
        return str(target)

    def init_corpus(self, *, repo_root: str, overwrite: bool = False) -> dict[str, Any]:
        self._ensure_benchmark_target(repo_root)
        corpus_file = self._tasks_file(repo_root)
        if corpus_file.exists() and not overwrite:
            return {"ok": True, "created": False, "corpus_file": str(corpus_file)}

        payload = _build_default_benchmark_corpus()
        corpus_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return {
            "ok": True,
            "created": True,
            "corpus_file": str(corpus_file),
            "task_count": len(payload["tasks"]),
        }

    def _parse_tasks_payload(self, payload: Any) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        if isinstance(payload, list):
            tasks = [dict(item) for item in payload if isinstance(item, dict)]
            return tasks, {"version": "legacy", "name": "legacy-fixed-tasks"}

        if isinstance(payload, dict):
            raw_tasks = payload.get("tasks")
            if isinstance(raw_tasks, list):
                tasks = [dict(item) for item in raw_tasks if isinstance(item, dict)]
                meta = {
                    "version": str(payload.get("version") or "unknown"),
                    "name": str(payload.get("name") or "custom-corpus"),
                    "description": str(payload.get("description") or ""),
                }
                return tasks, meta

        return [], {}

    def validate_tasks(self, tasks: list[dict[str, Any]]) -> dict[str, Any]:
        errors: list[str] = []
        valid_task_types = {"auto", "agent", "analyze", "edit"}
        for idx, task in enumerate(tasks, start=1):
            name = str(task.get("name") or f"task_{idx}")
            task_type = str(task.get("task_type") or "auto")
            if task_type not in valid_task_types:
                errors.append(f"{name}: 不支援的 task_type={task_type}")
                continue
            if task_type == "edit":
                relative_path = str(task.get("relative_path") or "").strip()
                if not relative_path:
                    errors.append(f"{name}: edit 任務缺少 relative_path")
            else:
                user_request = str(task.get("user_request") or "").strip()
                if not user_request:
                    errors.append(f"{name}: {task_type} 任務缺少 user_request")

        return {"ok": len(errors) == 0, "errors": errors, "total": len(tasks)}

    def load_tasks(self, *, repo_root: str, tasks_file: str | None = None) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        self._ensure_benchmark_target(repo_root)

        if tasks_file:
            path = Path(tasks_file).expanduser()
            if not path.is_absolute():
                path = Path(repo_root).resolve() / path
            if not path.exists():
                self.init_corpus(repo_root=repo_root, overwrite=False)
                payload = _build_default_benchmark_corpus()
                tasks, meta = self._parse_tasks_payload(payload)
                meta["source"] = "default-fallback-missing-custom"
                return tasks, meta
            payload = json.loads(path.read_text(encoding="utf-8"))
            tasks, meta = self._parse_tasks_payload(payload)
            meta["source"] = str(path)
            return tasks, meta

        corpus_path = self._tasks_file(repo_root)
        legacy_path = self._legacy_tasks_file(repo_root)

        if not corpus_path.exists():
            if legacy_path.exists():
                payload = json.loads(legacy_path.read_text(encoding="utf-8"))
                tasks, meta = self._parse_tasks_payload(payload)
                meta["source"] = str(legacy_path)
                return tasks, meta
            self.init_corpus(repo_root=repo_root, overwrite=False)

        payload = json.loads(corpus_path.read_text(encoding="utf-8"))
        tasks, meta = self._parse_tasks_payload(payload)
        meta["source"] = str(corpus_path)
        return tasks, meta

    def run(self, *, repo_root: str, threshold: float = 0.85, tasks_file: str | None = None) -> dict[str, Any]:
        tasks, corpus_meta = self.load_tasks(repo_root=repo_root, tasks_file=tasks_file)
        validation = self.validate_tasks(tasks)
        if not validation["ok"]:
            return {
                "ok": False,
                "error": "benchmark 任務集格式不正確",
                "validation": validation,
                "corpus": corpus_meta,
            }

        started = time.time()
        results: list[dict[str, Any]] = []

        for idx, task in enumerate(tasks, start=1):
            task_name = str(task.get("name") or f"task_{idx}")
            task_type = str(task.get("task_type") or "auto")
            user_request = str(task.get("user_request") or "")
            output = self._orchestrator.run(
                repo_root=repo_root,
                task_type=task_type,
                user_request=user_request,
                relative_path=str(task.get("relative_path") or "README.md"),
                content=str(task.get("content") or ""),
                mode=str(task.get("mode") or "append"),
                old_text=(str(task["old_text"]) if task.get("old_text") is not None else None),
                operations=(list(task.get("operations")) if isinstance(task.get("operations"), list) else None),
                metadata={"benchmark_task": task_name},
            )
            ok = bool(output.get("ok"))
            results.append(
                {
                    "name": task_name,
                    "ok": ok,
                    "task_type": task_type,
                    "user_request": user_request,
                    "selected_skill": output.get("selected_skill"),
                    "task_state": output.get("task_state"),
                    "trace_ref": output.get("trace_ref"),
                    "error_code": (output.get("error") or {}).get("code") if isinstance(output.get("error"), dict) else None,
                    "chain_to": list(output.get("chain_to") or []),
                    "fallback_skills": list(output.get("fallback_skills") or []),
                }
            )

        total = len(results)
        success = len([item for item in results if item["ok"]])
        success_rate = (success / total) if total else 0.0
        passed = success_rate >= threshold
        elapsed_ms = int((time.time() - started) * 1000)

        observability = self._observability.summarize_results(results)
        report = {
            "ok": True,
            "threshold": threshold,
            "success": success,
            "total": total,
            "success_rate": round(success_rate, 4),
            "passed": passed,
            "elapsed_ms": elapsed_ms,
            "results": results,
            "routing_observability": observability,
            "corpus": corpus_meta,
            "validation": validation,
        }

        timestamp = int(time.time() * 1000)
        report_file = self._reports_dir(repo_root) / f"benchmark-{timestamp}.json"
        report_file.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        latest_file = self._bench_dir(repo_root) / "latest.json"
        latest_file.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        report["report_file"] = str(report_file)
        report["latest_file"] = str(latest_file)
        return report

    def report(self, *, repo_root: str) -> dict[str, Any]:
        latest = self._bench_dir(repo_root) / "latest.json"
        if not latest.exists():
            return {"ok": False, "error": "benchmark report not found, run benchmark first"}
        payload = json.loads(latest.read_text(encoding="utf-8"))
        payload["ok"] = True
        payload["latest_file"] = str(latest)
        payload["session_observability"] = self._observability.summarize_agent_sessions(repo_root)
        return payload
