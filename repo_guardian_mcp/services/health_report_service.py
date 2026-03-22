from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from repo_guardian_mcp.services.benchmark_service import BenchmarkService
from repo_guardian_mcp.services.routing_observability_service import RoutingObservabilityService
from repo_guardian_mcp.services.runtime_cleanup_service import RuntimeCleanupService


class HealthReportService:
    """整合 benchmark、觀測、runtime 壓力，輸出單一健康度報表。"""

    def __init__(
        self,
        *,
        benchmark: BenchmarkService | None = None,
        observability: RoutingObservabilityService | None = None,
        runtime_cleanup: RuntimeCleanupService | None = None,
    ) -> None:
        self.benchmark = benchmark or BenchmarkService()
        self.observability = observability or RoutingObservabilityService()
        self.runtime_cleanup = runtime_cleanup or RuntimeCleanupService()

    def _dir_size_mb(self, path: Path) -> float:
        if not path.exists():
            return 0.0
        total = 0
        for file in path.rglob("*"):
            if file.is_file():
                try:
                    total += file.stat().st_size
                except OSError:
                    continue
        return round(total / (1024 * 1024), 2)

    def _health_dir(self, repo_root: str) -> Path:
        path = Path(repo_root).resolve() / "agent_runtime" / "health"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _reports_dir(self, repo_root: str) -> Path:
        path = self._health_dir(repo_root) / "reports"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def report(
        self,
        *,
        repo_root: str,
        refresh_benchmark: bool = False,
        threshold: float = 0.85,
        save: bool = True,
    ) -> dict[str, Any]:
        root = Path(repo_root).resolve()
        runtime_root = root / "agent_runtime"
        benchmark_payload: dict[str, Any] | None = None
        benchmark_ok = False

        if refresh_benchmark:
            benchmark_payload = self.benchmark.run(repo_root=str(root), threshold=threshold)
            benchmark_ok = bool(benchmark_payload.get("ok"))
        else:
            report_payload = self.benchmark.report(repo_root=str(root))
            if report_payload.get("ok"):
                benchmark_payload = report_payload
                benchmark_ok = True

        routing = self.observability.summarize_agent_sessions(str(root))
        runtime_dry_run = self.runtime_cleanup.run(
            repo_root=str(root),
            session_days=3,
            max_sessions=20,
            agent_session_days=14,
            keep_last_agent_sessions=30,
            orphan_workspace_days=3,
            dry_run=True,
        )

        footprint = {
            "runtime_total_mb": self._dir_size_mb(runtime_root),
            "sandbox_workspaces_mb": self._dir_size_mb(runtime_root / "sandbox_workspaces"),
            "sessions_mb": self._dir_size_mb(runtime_root / "sessions"),
            "agent_sessions_mb": self._dir_size_mb(runtime_root / "agent_sessions"),
        }

        score = 100
        issues: list[str] = []

        if not benchmark_ok:
            score -= 15
            issues.append("尚未建立 benchmark 報表，建議先跑 benchmark run。")
        else:
            success_rate = float(benchmark_payload.get("success_rate", 0.0))
            if success_rate < threshold:
                score -= 30
                issues.append(f"benchmark 成功率偏低（{success_rate:.2%} < {threshold:.0%}）。")

        reclaim_mb = float(runtime_dry_run.get("reclaimed_mb") or 0.0)
        if reclaim_mb > 512:
            score -= 30
            issues.append("runtime 可回收空間過大，建議立即清理。")
        elif reclaim_mb > 128:
            score -= 20
            issues.append("runtime 有明顯空間壓力，建議近期清理。")
        elif reclaim_mb > 32:
            score -= 10
            issues.append("runtime 有可回收空間，建議排程清理。")

        error_count = sum(int(v) for v in (routing.get("last_error_counts") or {}).values())
        if error_count > 0:
            score -= min(20, error_count * 2)
            issues.append(f"近期 agent session 有錯誤紀錄（{error_count} 筆）。")

        score = max(0, min(100, score))
        if score >= 80:
            health_level = "good"
        elif score >= 60:
            health_level = "warning"
        else:
            health_level = "critical"

        next_actions: list[str] = []
        if not benchmark_ok:
            next_actions.append("先執行 benchmark run 建立基準線。")
        if reclaim_mb > 0:
            next_actions.append("執行 runtime-cleanup run 釋放空間。")
        if error_count > 0:
            next_actions.append("檢查 observe routing 與最近失敗 session。")
        if not next_actions:
            next_actions.append("狀態健康，維持每日排程即可。")

        output = {
            "ok": True,
            "repo_root": str(root),
            "health_score": score,
            "health_level": health_level,
            "issues": issues,
            "benchmark_ok": benchmark_ok,
            "benchmark": benchmark_payload,
            "routing_observability": routing,
            "runtime_cleanup_dry_run": runtime_dry_run,
            "runtime_footprint_mb": footprint,
            "user_friendly_summary": f"目前健康度 {score}/100（{health_level}）。",
            "next_actions": next_actions,
        }
        if save:
            ts = int(time.time() * 1000)
            report_file = self._reports_dir(str(root)) / f"health-{ts}.json"
            latest_file = self._health_dir(str(root)) / "latest.json"
            report_file.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
            latest_file.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
            output["report_file"] = str(report_file)
            output["latest_file"] = str(latest_file)
        return output

    def history(self, *, repo_root: str, limit: int = 30) -> dict[str, Any]:
        reports_dir = self._reports_dir(repo_root)
        rows: list[dict[str, Any]] = []
        for path in sorted(reports_dir.glob("health-*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            rows.append(
                {
                    "timestamp_ms": int(path.stat().st_mtime * 1000),
                    "health_score": payload.get("health_score"),
                    "health_level": payload.get("health_level"),
                    "issues_count": len(payload.get("issues") or []),
                    "report_file": str(path),
                }
            )
        if limit > 0:
            rows = rows[:limit]
        scores = [int(item["health_score"]) for item in rows if isinstance(item.get("health_score"), int)]
        average = round(sum(scores) / len(scores), 2) if scores else None
        trend = "flat"
        if len(scores) >= 2:
            if scores[0] > scores[-1]:
                trend = "up"
            elif scores[0] < scores[-1]:
                trend = "down"

        return {
            "ok": True,
            "repo_root": str(Path(repo_root).resolve()),
            "count": len(rows),
            "average_score": average,
            "trend": trend,
            "items": rows,
            "user_friendly_summary": (
                f"共 {len(rows)} 筆健康紀錄，平均分數 {average}。"
                if rows
                else "目前還沒有健康度歷史紀錄。"
            ),
            "next_actions": (
                ["先執行 health report 產生第一筆紀錄。"]
                if not rows
                else ["可持續觀察趨勢，必要時補跑 benchmark 與 cleanup。"]
            ),
        }

    def build_windows_schedule_hint(
        self,
        *,
        repo_root: str,
        at_time: str = "03:45",
        task_name: str = "RepoGuardianHealthReport",
        refresh_benchmark: bool = False,
    ) -> dict[str, Any]:
        refresh_arg = " --refresh-benchmark" if refresh_benchmark else ""
        cmd = (
            f'schtasks /Create /F /SC DAILY /TN "{task_name}" /ST {at_time} '
            f'/TR "cmd /c cd /d {repo_root} && uv run repo-guardian health report .{refresh_arg}"'
        )
        return {
            "ok": True,
            "task_name": task_name,
            "time": at_time,
            "refresh_benchmark": refresh_benchmark,
            "schedule_command": cmd,
            "note": "請用系統管理員權限執行此指令。",
        }
