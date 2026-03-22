from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from repo_guardian_mcp.services.continue_config_service import ContinueConfigService
from repo_guardian_mcp.services.health_report_service import HealthReportService
from repo_guardian_mcp.services.ide_bridge_service import IDEBridgeService
from repo_guardian_mcp.services.runtime_cleanup_service import RuntimeCleanupService


class OpsService:
    """維運流程聚合服務：preflight / daily / snapshot。"""

    def __init__(
        self,
        *,
        continue_config: ContinueConfigService | None = None,
        health: HealthReportService | None = None,
        bridge: IDEBridgeService | None = None,
        runtime_cleanup: RuntimeCleanupService | None = None,
    ) -> None:
        self.continue_config = continue_config or ContinueConfigService()
        self.health = health or HealthReportService()
        self.bridge = bridge or IDEBridgeService()
        self.runtime_cleanup = runtime_cleanup or RuntimeCleanupService()

    def _ops_dir(self, repo_root: str) -> Path:
        path = Path(repo_root).resolve() / "agent_runtime" / "ops"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _build_score(self, checks: list[dict[str, Any]]) -> int:
        score = 100
        for check in checks:
            if not check.get("ok"):
                score -= int(check.get("penalty", 0))
        return max(0, min(100, score))

    def preflight(
        self,
        *,
        repo_root: str,
        continue_source_config: str = "continue/config.yaml",
        continue_target_config: str | None = None,
    ) -> dict[str, Any]:
        root = Path(repo_root).resolve()
        target_cfg = continue_target_config or str(Path.home() / ".continue" / "config.yaml")
        cfg = self.continue_config.status(
            source_config=str((root / continue_source_config).resolve())
            if not Path(continue_source_config).is_absolute()
            else continue_source_config,
            target_config=target_cfg,
        )
        health = self.health.report(repo_root=str(root), refresh_benchmark=False, threshold=0.85, save=False)
        bridge_queue = self.bridge.queue(repo_root=str(root), limit=30)
        runtime_dry = self.runtime_cleanup.run(
            repo_root=str(root),
            session_days=3,
            max_sessions=20,
            agent_session_days=14,
            keep_last_agent_sessions=30,
            orphan_workspace_days=3,
            dry_run=True,
        )

        checks = [
            {
                "name": "continue_config_synced",
                "ok": bool(cfg.get("ok")) and bool(cfg.get("same_content")),
                "penalty": 20,
                "message": "Continue 設定已同步。" if cfg.get("same_content") else "Continue 設定尚未同步。",
            },
            {
                "name": "health_score",
                "ok": int(health.get("health_score") or 0) >= 70,
                "penalty": 30,
                "message": f"健康分數 {health.get('health_score', 0)}。",
            },
            {
                "name": "runtime_pressure",
                "ok": float(runtime_dry.get("reclaimed_mb") or 0.0) < 256,
                "penalty": 20,
                "message": f"可回收空間 {runtime_dry.get('reclaimed_mb', 0)} MB。",
            },
            {
                "name": "bridge_queue_not_backlogged",
                "ok": int((bridge_queue.get("counts") or {}).get("running", 0)) < 10,
                "penalty": 10,
                "message": f"bridge running={(bridge_queue.get('counts') or {}).get('running', 0)}。",
            },
        ]
        score = self._build_score(checks)
        ready = score >= 70
        return {
            "ok": True,
            "repo_root": str(root),
            "ready": ready,
            "preflight_score": score,
            "checks": checks,
            "continue_config_status": cfg,
            "health": health,
            "bridge_queue": bridge_queue,
            "runtime_cleanup_dry_run": runtime_dry,
            "user_friendly_summary": "環境可上線使用。" if ready else "環境尚未達到建議上線門檻。",
            "next_actions": (
                ["可開始日常開發。"]
                if ready
                else [
                    "先同步 Continue 設定。",
                    "先清理 runtime 空間或補跑 benchmark。",
                ]
            ),
        }

    def daily(self, *, repo_root: str, refresh_benchmark: bool = False) -> dict[str, Any]:
        root = Path(repo_root).resolve()
        health = self.health.report(repo_root=str(root), refresh_benchmark=refresh_benchmark, threshold=0.85, save=True)
        queue = self.bridge.queue(repo_root=str(root), limit=50)
        history = self.health.history(repo_root=str(root), limit=7)
        return {
            "ok": True,
            "repo_root": str(root),
            "health": health,
            "bridge_queue": queue,
            "health_history": history,
            "user_friendly_summary": f"今日巡檢完成，健康分數 {health.get('health_score')}。",
            "next_actions": health.get("next_actions") or ["持續觀察趨勢。"],
        }

    def snapshot(self, *, repo_root: str, tag: str | None = None) -> dict[str, Any]:
        root = Path(repo_root).resolve()
        ts = int(time.time() * 1000)
        tag = tag or "manual"
        preflight = self.preflight(repo_root=str(root))
        daily = self.daily(repo_root=str(root), refresh_benchmark=False)
        payload = {
            "ok": True,
            "tag": tag,
            "timestamp_ms": ts,
            "preflight": preflight,
            "daily": daily,
        }
        file = self._ops_dir(str(root)) / f"snapshot-{tag}-{ts}.json"
        file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        payload["snapshot_file"] = str(file)
        payload["user_friendly_summary"] = "已產生維運快照。"
        payload["next_actions"] = ["可用此快照做回顧或交接。"]
        return payload

    def run(
        self,
        *,
        repo_root: str,
        profile: str = "day-start",
        continue_source_config: str = "continue/config.yaml",
        continue_target_config: str | None = None,
        refresh_benchmark: bool = False,
        snapshot_tag: str | None = None,
    ) -> dict[str, Any]:
        profile = (profile or "day-start").strip().lower()
        root = Path(repo_root).resolve()
        allowed = {"day-start", "day-end", "release-check"}
        if profile not in allowed:
            return {
                "ok": False,
                "error": f"未知 profile: {profile}，可用值：day-start/day-end/release-check",
                "profile": profile,
            }

        preflight = self.preflight(
            repo_root=str(root),
            continue_source_config=continue_source_config,
            continue_target_config=continue_target_config,
        )

        if profile == "day-start":
            daily = self.daily(repo_root=str(root), refresh_benchmark=refresh_benchmark)
            result = {
                "ok": True,
                "profile": profile,
                "preflight": preflight,
                "daily": daily,
                "user_friendly_summary": "day-start 已完成：已做上線前檢查與今日巡檢。",
                "next_actions": ["可開始今天的開發工作。"],
            }
            return result

        if profile == "day-end":
            daily = self.daily(repo_root=str(root), refresh_benchmark=refresh_benchmark)
            snap = self.snapshot(repo_root=str(root), tag=snapshot_tag or "day-end")
            result = {
                "ok": True,
                "profile": profile,
                "daily": daily,
                "snapshot": snap,
                "user_friendly_summary": "day-end 已完成：已巡檢並產生收工快照。",
                "next_actions": ["可結束今日工作，明天用 snapshot 回顧。"],
            }
            return result

        # release-check
        daily = self.daily(repo_root=str(root), refresh_benchmark=True)
        snap = self.snapshot(repo_root=str(root), tag=snapshot_tag or "release-check")
        ready = bool((preflight.get("ready")) and (daily.get("health") or {}).get("health_score", 0) >= 80)
        return {
            "ok": True,
            "profile": profile,
            "ready": ready,
            "preflight": preflight,
            "daily": daily,
            "snapshot": snap,
            "user_friendly_summary": "release-check 完成，可依結果決定是否發版。",
            "next_actions": (
                ["檢查通過，可進入發版流程。"]
                if ready
                else ["尚未達標，請先處理 preflight 或健康度問題。"]
            ),
        }
