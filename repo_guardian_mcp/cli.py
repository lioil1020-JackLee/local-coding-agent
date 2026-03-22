from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from repo_guardian_mcp.services.cli_agent_service import CLIAgentService
from repo_guardian_mcp.services.benchmark_service import BenchmarkService
from repo_guardian_mcp.services.cli_chat_service import CLIChatService
from repo_guardian_mcp.services.continue_e2e_service import ContinueE2EService
from repo_guardian_mcp.services.continue_config_service import ContinueConfigService
from repo_guardian_mcp.services.health_report_service import HealthReportService
from repo_guardian_mcp.services.ide_bridge_service import IDEBridgeService
from repo_guardian_mcp.services.ops_service import OpsService
from repo_guardian_mcp.services.response_envelope_service import ResponseEnvelopeService
from repo_guardian_mcp.services.runtime_cleanup_service import RuntimeCleanupService
from repo_guardian_mcp.services.routing_observability_service import RoutingObservabilityService
from repo_guardian_mcp.services.session_lifecycle_contract_service import SessionLifecycleContractService
from repo_guardian_mcp.services.task_state_machine import TaskState


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="repo-guardian",
        description="Local CLI coding agent with safe-edit workflows.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("repo_root")
    common.add_argument("--prompt", default="")
    common.add_argument("--task-type", default="auto", choices=["auto", "agent", "edit", "analyze"])
    common.add_argument("--relative-path", default="README.md")
    common.add_argument("--content", default="")
    common.add_argument("--mode", default="append", choices=["append", "prepend", "replace"])
    common.add_argument("--old-text", default=None)
    common.add_argument("--session-id", default=None)
    common.add_argument("--operations-json", default=None)
    common.add_argument("--skill", default=None)

    sub.add_parser("skills", help="列出可用 skills")
    sub.add_parser("plan", parents=[common], help="先產生任務計畫")
    sub.add_parser("run", parents=[common], help="直接執行任務")

    chat_parser = sub.add_parser("chat", help="進入 chat 模式")
    chat_parser.add_argument("repo_root")
    chat_parser.add_argument("--task-type", default="auto", choices=["auto", "agent", "edit", "analyze"])
    chat_parser.add_argument("--message", default=None, help="單次訊息")
    chat_parser.add_argument("--once", action="store_true", help="搭配 --message 使用，只執行一次")

    session_parser = sub.add_parser("session", help="session 管理")
    session_sub = session_parser.add_subparsers(dest="session_command", required=True)
    session_list = session_sub.add_parser("list", help="列出 sessions")
    session_list.add_argument("repo_root")
    session_list.add_argument("--include-cleaned", action="store_true")
    session_resume = session_sub.add_parser("resume", help="讀取指定 session")
    session_resume.add_argument("repo_root")
    session_resume.add_argument("session_id")

    diff_parser = sub.add_parser("diff", help="查詢指定 session 與 repo 的差異")
    diff_parser.add_argument("repo_root")
    diff_parser.add_argument("session_id")

    rollback_parser = sub.add_parser("rollback", help="回滾指定 session")
    rollback_parser.add_argument("repo_root")
    rollback_parser.add_argument("session_id")
    rollback_parser.add_argument("--keep-workspace", action="store_true", help="回滾後保留 sandbox")

    bridge = sub.add_parser("bridge", help="IDE bridge 相關命令")
    bridge_sub = bridge.add_subparsers(dest="bridge_command", required=True)
    bridge_invoke = bridge_sub.add_parser("invoke", help="送 prompt 到 bridge")
    bridge_invoke.add_argument("repo_root")
    bridge_invoke.add_argument("--prompt", required=True)
    bridge_invoke.add_argument("--task-type", default="auto", choices=["auto", "agent", "edit", "analyze"])
    bridge_invoke.add_argument("--session-id", default=None)
    bridge_invoke.add_argument("--plan-only", action="store_true")
    bridge_status = bridge_sub.add_parser("status", help="查 bridge 任務狀態")
    bridge_status.add_argument("repo_root")
    bridge_status.add_argument("task_id")
    bridge_trace = bridge_sub.add_parser("trace", help="查 bridge trace")
    bridge_trace.add_argument("repo_root")
    bridge_trace.add_argument("task_id")
    bridge_diagnose = bridge_sub.add_parser("diagnose", help="查 bridge 任務診斷")
    bridge_diagnose.add_argument("repo_root")
    bridge_diagnose.add_argument("task_id")
    bridge_diff = bridge_sub.add_parser("diff", help="查 session diff")
    bridge_diff.add_argument("repo_root")
    bridge_diff.add_argument("session_id")
    bridge_rollback = bridge_sub.add_parser("rollback", help="回滾 session")
    bridge_rollback.add_argument("repo_root")
    bridge_rollback.add_argument("session_id")
    bridge_events = bridge_sub.add_parser("events", help="查 bridge 事件流")
    bridge_events.add_argument("repo_root")
    bridge_events.add_argument("task_id")
    bridge_events.add_argument("--limit", type=int, default=50)
    bridge_list = bridge_sub.add_parser("list", help="列出近期 bridge 任務")
    bridge_list.add_argument("repo_root")
    bridge_list.add_argument("--limit", type=int, default=20)
    bridge_latest = bridge_sub.add_parser("latest", help="查最新 bridge 任務整體資訊")
    bridge_latest.add_argument("repo_root")
    bridge_cleanup = bridge_sub.add_parser("cleanup", help="清理舊 bridge 任務")
    bridge_cleanup.add_argument("repo_root")
    bridge_cleanup.add_argument("--days", type=int, default=7)
    bridge_cleanup.add_argument("--keep", type=int, default=200)
    bridge_cleanup.add_argument("--dry-run", action="store_true")
    bridge_queue = bridge_sub.add_parser("queue", help="bridge 佇列聚合視圖")
    bridge_queue.add_argument("repo_root")
    bridge_queue.add_argument("--limit", type=int, default=50)

    benchmark = sub.add_parser("benchmark", help="固定任務集基準測試")
    benchmark_sub = benchmark.add_subparsers(dest="benchmark_command", required=True)
    bench_init = benchmark_sub.add_parser("init", help="初始化 benchmark 任務集")
    bench_init.add_argument("repo_root")
    bench_init.add_argument("--overwrite", action="store_true")
    bench_run = benchmark_sub.add_parser("run", help="執行 benchmark")
    bench_run.add_argument("repo_root")
    bench_run.add_argument("--threshold", type=float, default=0.85)
    bench_run.add_argument("--tasks-file", default=None, help="指定 benchmark 任務集 JSON（可用相對路徑）")
    bench_report = benchmark_sub.add_parser("report", help="讀取最新 benchmark 報表")
    bench_report.add_argument("repo_root")

    observe = sub.add_parser("observe", help="routing/fallback/chaining 可觀測資訊")
    observe_sub = observe.add_subparsers(dest="observe_command", required=True)
    observe_routing = observe_sub.add_parser("routing", help="讀取 routing 觀測摘要")
    observe_routing.add_argument("repo_root")

    continue_e2e = sub.add_parser("continue-e2e", help="Continue 鏈路端到端檢查")
    continue_e2e_sub = continue_e2e.add_subparsers(dest="continue_e2e_command", required=True)
    continue_e2e_run = continue_e2e_sub.add_parser("run", help="執行 Continue e2e")
    continue_e2e_run.add_argument("repo_root")

    continue_cfg = sub.add_parser("continue-config", help="Continue 設定檢查與同步")
    continue_cfg_sub = continue_cfg.add_subparsers(dest="continue_cfg_command", required=True)
    cfg_status = continue_cfg_sub.add_parser("status", help="檢查來源與目標設定差異")
    cfg_status.add_argument("--source-config", default="continue/config.yaml")
    cfg_status.add_argument("--target-config", default=str(Path.home() / ".continue" / "config.yaml"))
    cfg_sync = continue_cfg_sub.add_parser("sync", help="同步 Continue 設定")
    cfg_sync.add_argument("--source-config", default="continue/config.yaml")
    cfg_sync.add_argument("--target-config", default=str(Path.home() / ".continue" / "config.yaml"))
    cfg_sync.add_argument("--with-assets", action="store_true", help="同步 rules 與 system-prompts")
    cfg_diagnose = continue_cfg_sub.add_parser("diagnose", help="檢查 Continue/Cursor 可用性並給修復建議")
    cfg_diagnose.add_argument("repo_root")
    cfg_diagnose.add_argument("--source-config", default="continue/config.yaml")
    cfg_diagnose.add_argument("--target-config", default=None)
    cfg_diagnose.add_argument("--target-profile", default="cursor", choices=["cursor", "continue-default"])
    cfg_diagnose.add_argument("--without-assets", action="store_true", help="不檢查 rules/prompts 同步")
    cfg_autofix = continue_cfg_sub.add_parser("autofix", help="依診斷結果自動修復 Continue/Cursor 設定")
    cfg_autofix.add_argument("repo_root")
    cfg_autofix.add_argument("--source-config", default="continue/config.yaml")
    cfg_autofix.add_argument("--target-config", default=None)
    cfg_autofix.add_argument("--target-profile", default="cursor", choices=["cursor", "continue-default"])
    cfg_autofix.add_argument("--without-assets", action="store_true", help="只修復 config.yaml，不同步 rules/prompts")
    cfg_autofix.add_argument("--no-backup", action="store_true", help="不備份既有目標設定")
    cfg_autofix.add_argument("--dry-run", action="store_true", help="只預檢，不實際修復")
    cfg_autofix.add_argument("--run-e2e", action="store_true", help="修復後順便跑 continue-e2e")
    cfg_setup = continue_cfg_sub.add_parser("setup", help="一鍵設定 Continue/Cursor（新手建議）")
    cfg_setup.add_argument("repo_root")
    cfg_setup.add_argument("--source-config", default="continue/config.yaml")
    cfg_setup.add_argument("--target-config", default=None)
    cfg_setup.add_argument("--target-profile", default="cursor", choices=["cursor", "continue-default"])
    cfg_setup.add_argument("--without-assets", action="store_true", help="只同步 config.yaml，不同步 rules/prompts")
    cfg_setup.add_argument("--no-backup", action="store_true", help="不備份既有目標設定")
    cfg_setup.add_argument("--dry-run", action="store_true", help="只檢查不寫入")
    cfg_setup.add_argument("--run-e2e", action="store_true", help="setup 後順便跑 continue-e2e")

    runtime_cleanup = sub.add_parser("runtime-cleanup", help="清理 agent_runtime 空間")
    runtime_cleanup_sub = runtime_cleanup.add_subparsers(dest="runtime_cleanup_command", required=True)
    cleanup_run = runtime_cleanup_sub.add_parser("run", help="執行 runtime 清理")
    cleanup_run.add_argument("repo_root")
    cleanup_run.add_argument("--session-days", type=int, default=3)
    cleanup_run.add_argument("--max-sessions", type=int, default=20)
    cleanup_run.add_argument("--max-total-workspace-gb", type=float, default=None)
    cleanup_run.add_argument("--agent-session-days", type=int, default=14)
    cleanup_run.add_argument("--keep-last-agent-sessions", type=int, default=30)
    cleanup_run.add_argument("--orphan-workspace-days", type=int, default=3)
    cleanup_run.add_argument("--dry-run", action="store_true")
    cleanup_run.add_argument("--aggressive", action="store_true", help="更積極清理（保留天數與數量更低）")
    cleanup_hint = runtime_cleanup_sub.add_parser("schedule-hint", help="產生 Windows 排程建議")
    cleanup_hint.add_argument("repo_root")
    cleanup_hint.add_argument("--time", default="03:30")
    cleanup_hint.add_argument("--task-name", default="RepoGuardianRuntimeCleanup")

    health = sub.add_parser("health", help="健康度報告")
    health_sub = health.add_subparsers(dest="health_command", required=True)
    health_report = health_sub.add_parser("report", help="輸出健康度報告")
    health_report.add_argument("repo_root")
    health_report.add_argument("--refresh-benchmark", action="store_true")
    health_report.add_argument("--threshold", type=float, default=0.85)
    health_report.add_argument("--no-save", action="store_true")
    health_history = health_sub.add_parser("history", help="讀取歷史健康報告")
    health_history.add_argument("repo_root")
    health_history.add_argument("--limit", type=int, default=30)
    health_hint = health_sub.add_parser("schedule-hint", help="產生健康報告排程建議")
    health_hint.add_argument("repo_root")
    health_hint.add_argument("--time", default="03:45")
    health_hint.add_argument("--task-name", default="RepoGuardianHealthReport")
    health_hint.add_argument("--refresh-benchmark", action="store_true")

    ops = sub.add_parser("ops", help="日常維運命令")
    ops_sub = ops.add_subparsers(dest="ops_command", required=True)
    ops_preflight = ops_sub.add_parser("preflight", help="開工前檢查")
    ops_preflight.add_argument("repo_root")
    ops_preflight.add_argument("--continue-source-config", default="continue/config.yaml")
    ops_preflight.add_argument("--continue-target-config", default=str(Path.home() / ".continue" / "config.yaml"))
    ops_daily = ops_sub.add_parser("daily", help="每日維運報告")
    ops_daily.add_argument("repo_root")
    ops_daily.add_argument("--refresh-benchmark", action="store_true")
    ops_snapshot = ops_sub.add_parser("snapshot", help="產生維運快照")
    ops_snapshot.add_argument("repo_root")
    ops_snapshot.add_argument("--tag", default="manual")
    ops_run = ops_sub.add_parser("run", help="一鍵執行維運流程")
    ops_run.add_argument("repo_root")
    ops_run.add_argument("--profile", default="day-start", choices=["day-start", "day-end", "release-check"])
    ops_run.add_argument("--continue-source-config", default="continue/config.yaml")
    ops_run.add_argument("--continue-target-config", default=str(Path.home() / ".continue" / "config.yaml"))
    ops_run.add_argument("--refresh-benchmark", action="store_true")
    ops_run.add_argument("--snapshot-tag", default=None)

    return parser


def _parse_operations(raw: str | None) -> list[dict[str, Any]] | None:
    if not raw:
        return None
    value = json.loads(raw)
    if not isinstance(value, list):
        raise ValueError("operations-json 必須是 JSON list")
    return value


def _print_json(data: dict[str, Any]) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def _print_chat_turn(turn, envelope_service: ResponseEnvelopeService) -> None:
    envelope = envelope_service.wrap(
        ok=turn.ok,
        mode=turn.mode,
        message=turn.message,
        data=dict(turn.payload),
        error=(turn.payload.get("error") if isinstance(turn.payload, dict) else None) if not turn.ok else None,
    )
    _print_json(envelope)


def _run_chat(repo_root: str, task_type: str, message: str | None, once: bool, envelope_service: ResponseEnvelopeService) -> int:
    chat = CLIChatService()
    if message is not None:
        turn = chat.handle_input(repo_root=repo_root, raw_text=message, default_task_type=task_type)
        _print_chat_turn(turn, envelope_service)
        return 0 if turn.ok else 1

    print("repo-guardian chat 已啟動，輸入 /help 查看指令，輸入 /exit 離開。")
    while True:
        try:
            raw = input("repo-guardian> ")
        except EOFError:
            print("已離開 chat。")
            return 0
        turn = chat.handle_input(repo_root=repo_root, raw_text=raw, default_task_type=task_type)
        if turn.mode == "noop" and not turn.message:
            if once:
                return 0
            continue
        _print_chat_turn(turn, envelope_service)
        if turn.mode == "exit":
            return 0
        if once:
            return 0 if turn.ok else 1


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    service = CLIAgentService()
    bridge = IDEBridgeService(agent_service=service)
    envelope_service = ResponseEnvelopeService()
    lifecycle = SessionLifecycleContractService()
    benchmark = BenchmarkService()
    observability = RoutingObservabilityService()
    continue_e2e = ContinueE2EService()
    continue_cfg = ContinueConfigService()
    runtime_cleanup = RuntimeCleanupService()
    health_report = HealthReportService()
    ops = OpsService()

    if args.command == "skills":
        _print_json(
            envelope_service.wrap(
                ok=True,
                mode="skills",
                message="skills 已載入。",
                data={"skills": service.skill_registry.list_skill_metadata()},
                previous_state=TaskState.RUNNING,
            )
        )
        return 0

    if args.command == "chat":
        return _run_chat(args.repo_root, args.task_type, args.message, args.once, envelope_service)

    if args.command == "session":
        if args.session_command == "list":
            result = lifecycle.list(repo_root=args.repo_root, include_cleaned=args.include_cleaned)
            _print_json(
                envelope_service.wrap(
                    ok=bool(result.get("ok")),
                    mode="session_list",
                    message="session 清單已取得。" if result.get("ok") else "session 清單查詢失敗。",
                    data=result,
                    error=result.get("error") if not result.get("ok") else None,
                    previous_state=TaskState.RUNNING,
                )
            )
            return 0 if result.get("ok") else 1

        if args.session_command == "resume":
            result = lifecycle.resume(repo_root=args.repo_root, session_id=args.session_id)
            _print_json(
                envelope_service.wrap(
                    ok=bool(result.get("ok")),
                    mode="session_resume",
                    message="session 已讀取。" if result.get("ok") else "session 讀取失敗。",
                    data=result,
                    error=result.get("error") if not result.get("ok") else None,
                    previous_state=TaskState.RUNNING,
                )
            )
            return 0 if result.get("ok") else 1

        parser.error("未知的 session 子命令")
        return 2

    if args.command == "diff":
        result = lifecycle.diff(repo_root=args.repo_root, session_id=args.session_id)
        _print_json(
            envelope_service.wrap(
                ok=bool(result.get("ok")),
                mode="diff",
                message="diff 已取得。" if result.get("ok") else "diff 查詢失敗。",
                data=result,
                error=result.get("error") if not result.get("ok") else None,
                previous_state=TaskState.RUNNING,
            )
        )
        return 0 if result.get("ok") else 1

    if args.command == "rollback":
        result = lifecycle.rollback(repo_root=args.repo_root, session_id=args.session_id, keep_workspace=args.keep_workspace)
        _print_json(
            envelope_service.wrap(
                ok=bool(result.get("ok")),
                mode="rollback",
                message="rollback 已完成。" if result.get("ok") else "rollback 失敗。",
                data=result,
                error=result.get("error") if not result.get("ok") else None,
                previous_state=TaskState.RUNNING,
            )
        )
        return 0 if result.get("ok") else 1

    if args.command == "bridge":
        if args.bridge_command == "invoke":
            result = bridge.invoke(
                repo_root=args.repo_root,
                prompt=args.prompt,
                task_type=args.task_type,
                session_id=args.session_id,
                plan_only=args.plan_only,
            )
            _print_json(
                envelope_service.wrap(
                    ok=bool(result.get("ok")),
                    mode="bridge_invoke",
                    message="bridge 任務已送出。",
                    data=result,
                    error=result.get("error") if not result.get("ok") else None,
                    previous_state=TaskState.RUNNING,
                )
            )
            return 0 if result.get("ok") else 1

        if args.bridge_command == "status":
            result = bridge.status(repo_root=args.repo_root, task_id=args.task_id)
            _print_json(
                envelope_service.wrap(
                    ok=bool(result.get("ok")),
                    mode="bridge_status",
                    message="bridge 狀態已取得。" if result.get("ok") else "bridge 狀態查詢失敗。",
                    data=result,
                    error=result.get("error") if not result.get("ok") else None,
                    previous_state=TaskState.RUNNING,
                )
            )
            return 0 if result.get("ok") else 1

        if args.bridge_command == "trace":
            result = bridge.trace(repo_root=args.repo_root, task_id=args.task_id)
            _print_json(
                envelope_service.wrap(
                    ok=bool(result.get("ok")),
                    mode="bridge_trace",
                    message="bridge trace 已取得。" if result.get("ok") else "bridge trace 查詢失敗。",
                    data=result,
                    error=result.get("error") if not result.get("ok") else None,
                    previous_state=TaskState.RUNNING,
                )
            )
            return 0 if result.get("ok") else 1

        if args.bridge_command == "diagnose":
            result = bridge.diagnose(repo_root=args.repo_root, task_id=args.task_id)
            _print_json(
                envelope_service.wrap(
                    ok=bool(result.get("ok")),
                    mode="bridge_diagnose",
                    message="bridge 診斷資訊已取得。" if result.get("ok") else "bridge 診斷查詢失敗。",
                    data=result,
                    error=result.get("error") if not result.get("ok") else None,
                    previous_state=TaskState.RUNNING,
                )
            )
            return 0 if result.get("ok") else 1

        if args.bridge_command == "diff":
            result = bridge.diff(repo_root=args.repo_root, session_id=args.session_id)
            _print_json(
                envelope_service.wrap(
                    ok=bool(result.get("ok")),
                    mode="bridge_diff",
                    message="bridge diff 已取得。" if result.get("ok") else "bridge diff 查詢失敗。",
                    data=result,
                    error=result.get("error") if not result.get("ok") else None,
                    previous_state=TaskState.RUNNING,
                )
            )
            return 0 if result.get("ok") else 1

        if args.bridge_command == "rollback":
            result = bridge.rollback(repo_root=args.repo_root, session_id=args.session_id)
            _print_json(
                envelope_service.wrap(
                    ok=bool(result.get("ok")),
                    mode="bridge_rollback",
                    message="bridge rollback 已完成。" if result.get("ok") else "bridge rollback 失敗。",
                    data=result,
                    error=result.get("error") if not result.get("ok") else None,
                    previous_state=TaskState.RUNNING,
                )
            )
            return 0 if result.get("ok") else 1

        if args.bridge_command == "events":
            result = bridge.events(repo_root=args.repo_root, task_id=args.task_id, limit=args.limit)
            _print_json(
                envelope_service.wrap(
                    ok=bool(result.get("ok")),
                    mode="bridge_events",
                    message="bridge events 已取得。" if result.get("ok") else "bridge events 查詢失敗。",
                    data=result,
                    error=result.get("error") if not result.get("ok") else None,
                    previous_state=TaskState.RUNNING,
                )
            )
            return 0 if result.get("ok") else 1

        if args.bridge_command == "list":
            result = bridge.list_tasks(repo_root=args.repo_root, limit=args.limit)
            _print_json(
                envelope_service.wrap(
                    ok=bool(result.get("ok")),
                    mode="bridge_list",
                    message="bridge 任務清單已取得。" if result.get("ok") else "bridge 任務清單查詢失敗。",
                    data=result,
                    error=result.get("error") if not result.get("ok") else None,
                    previous_state=TaskState.RUNNING,
                )
            )
            return 0 if result.get("ok") else 1

        if args.bridge_command == "latest":
            result = bridge.latest(repo_root=args.repo_root)
            _print_json(
                envelope_service.wrap(
                    ok=bool(result.get("ok")),
                    mode="bridge_latest",
                    message="最新 bridge 任務資訊已取得。" if result.get("ok") else "bridge latest 查詢失敗。",
                    data=result,
                    error=result.get("error") if not result.get("ok") else None,
                    previous_state=TaskState.RUNNING,
                )
            )
            return 0 if result.get("ok") else 1

        if args.bridge_command == "cleanup":
            result = bridge.cleanup(
                repo_root=args.repo_root,
                days=args.days,
                keep=args.keep,
                dry_run=args.dry_run,
            )
            _print_json(
                envelope_service.wrap(
                    ok=bool(result.get("ok")),
                    mode="bridge_cleanup",
                    message="bridge 清理已完成。",
                    data=result,
                    error=result.get("error") if not result.get("ok") else None,
                    previous_state=TaskState.VALIDATED if result.get("ok") else TaskState.FAILED,
                )
            )
            return 0 if result.get("ok") else 1

        if args.bridge_command == "queue":
            result = bridge.queue(repo_root=args.repo_root, limit=args.limit)
            _print_json(
                envelope_service.wrap(
                    ok=bool(result.get("ok")),
                    mode="bridge_queue",
                    message="bridge 佇列已取得。",
                    data=result,
                    error=result.get("error") if not result.get("ok") else None,
                    previous_state=TaskState.RUNNING,
                )
            )
            return 0 if result.get("ok") else 1

    if args.command == "benchmark":
        if args.benchmark_command == "init":
            result = benchmark.init_corpus(repo_root=args.repo_root, overwrite=bool(args.overwrite))
            _print_json(
                envelope_service.wrap(
                    ok=bool(result.get("ok")),
                    mode="benchmark_init",
                    message="benchmark 任務集已初始化。",
                    data=result,
                    error=result.get("error") if not result.get("ok") else None,
                    previous_state=TaskState.PLANNED,
                )
            )
            return 0 if result.get("ok") else 1

        if args.benchmark_command == "run":
            result = benchmark.run(repo_root=args.repo_root, threshold=args.threshold, tasks_file=args.tasks_file)
            _print_json(
                envelope_service.wrap(
                    ok=bool(result.get("ok")),
                    mode="benchmark_run",
                    message="benchmark 已完成。",
                    data=result,
                    error=result.get("error") if not result.get("ok") else None,
                    previous_state=TaskState.VALIDATED,
                )
            )
            return 0 if result.get("ok") else 1

        if args.benchmark_command == "report":
            result = benchmark.report(repo_root=args.repo_root)
            _print_json(
                envelope_service.wrap(
                    ok=bool(result.get("ok")),
                    mode="benchmark_report",
                    message="benchmark 報表已取得。" if result.get("ok") else "benchmark 報表查詢失敗。",
                    data=result,
                    error=result.get("error") if not result.get("ok") else None,
                    previous_state=TaskState.RUNNING,
                )
            )
            return 0 if result.get("ok") else 1

    if args.command == "observe":
        if args.observe_command == "routing":
            result = {"ok": True, "routing_observability": observability.summarize_agent_sessions(args.repo_root)}
            _print_json(
                envelope_service.wrap(
                    ok=True,
                    mode="observe_routing",
                    message="routing 觀測摘要已取得。",
                    data=result,
                    previous_state=TaskState.RUNNING,
                )
            )
            return 0

    if args.command == "continue-e2e":
        if args.continue_e2e_command == "run":
            result = continue_e2e.run(repo_root=args.repo_root)
            _print_json(
                envelope_service.wrap(
                    ok=bool(result.get("ok")),
                    mode="continue_e2e_run",
                    message="Continue e2e 已完成。",
                    data=result,
                    error=result.get("error") if not result.get("ok") else None,
                    previous_state=TaskState.VALIDATED,
                )
            )
            return 0 if result.get("ok") else 1

    if args.command == "continue-config":
        if args.continue_cfg_command == "status":
            result = continue_cfg.status(source_config=args.source_config, target_config=args.target_config)
            _print_json(
                envelope_service.wrap(
                    ok=bool(result.get("ok")),
                    mode="continue_config_status",
                    message="Continue 設定比對已完成。",
                    data=result,
                    error=result.get("error") if not result.get("ok") else None,
                    previous_state=TaskState.RUNNING,
                )
            )
            return 0 if result.get("ok") else 1

        if args.continue_cfg_command == "diagnose":
            result = continue_cfg.diagnose(
                repo_root=args.repo_root,
                source_config=args.source_config,
                target_config=args.target_config,
                target_profile=args.target_profile,
                with_assets=not bool(args.without_assets),
            )
            _print_json(
                envelope_service.wrap(
                    ok=bool(result.get("ok")),
                    mode="continue_config_diagnose",
                    message="Continue 診斷已完成。" if result.get("ok") else "Continue 診斷失敗。",
                    data=result,
                    error=result.get("error") if not result.get("ok") else None,
                    previous_state=TaskState.RUNNING if result.get("ok") else TaskState.FAILED,
                )
            )
            return 0 if result.get("ok") else 1

        if args.continue_cfg_command == "sync":
            result = continue_cfg.sync(
                source_config=args.source_config,
                target_config=args.target_config,
                with_assets=bool(args.with_assets),
            )
            _print_json(
                envelope_service.wrap(
                    ok=bool(result.get("ok")),
                    mode="continue_config_sync",
                    message="Continue 設定同步已完成。" if result.get("ok") else "Continue 設定同步失敗。",
                    data=result,
                    error=result.get("error") if not result.get("ok") else None,
                    previous_state=TaskState.VALIDATED if result.get("ok") else TaskState.FAILED,
                )
            )
            return 0 if result.get("ok") else 1

        if args.continue_cfg_command == "autofix":
            result = continue_cfg.autofix(
                repo_root=args.repo_root,
                source_config=args.source_config,
                target_config=args.target_config,
                target_profile=args.target_profile,
                with_assets=not bool(args.without_assets),
                backup=not bool(args.no_backup),
                dry_run=bool(args.dry_run),
                run_e2e=bool(args.run_e2e),
            )
            _print_json(
                envelope_service.wrap(
                    ok=bool(result.get("ok")),
                    mode="continue_config_autofix",
                    message="Continue autofix 已完成。" if result.get("ok") else "Continue autofix 尚未完成，請依建議處理。",
                    data=result,
                    error=result.get("error") if not result.get("ok") else None,
                    previous_state=TaskState.VALIDATED if result.get("ok") else TaskState.FAILED,
                )
            )
            return 0 if result.get("ok") else 1

        if args.continue_cfg_command == "setup":
            result = continue_cfg.setup(
                repo_root=args.repo_root,
                source_config=args.source_config,
                target_config=args.target_config,
                target_profile=args.target_profile,
                with_assets=not bool(args.without_assets),
                backup=not bool(args.no_backup),
                dry_run=bool(args.dry_run),
                run_e2e=bool(args.run_e2e),
            )
            _print_json(
                envelope_service.wrap(
                    ok=bool(result.get("ok")),
                    mode="continue_config_setup",
                    message="Continue setup 已完成。" if result.get("ok") else "Continue setup 未完成，請依建議修正。",
                    data=result,
                    error=result.get("error") if not result.get("ok") else None,
                    previous_state=TaskState.VALIDATED if result.get("ok") else TaskState.FAILED,
                )
            )
            return 0 if result.get("ok") else 1

    if args.command == "runtime-cleanup":
        if args.runtime_cleanup_command == "run":
            result = runtime_cleanup.run(
                repo_root=args.repo_root,
                session_days=args.session_days,
                max_sessions=args.max_sessions,
                max_total_workspace_gb=args.max_total_workspace_gb,
                agent_session_days=args.agent_session_days,
                keep_last_agent_sessions=args.keep_last_agent_sessions,
                orphan_workspace_days=args.orphan_workspace_days,
                dry_run=args.dry_run,
                aggressive=args.aggressive,
            )
            _print_json(
                envelope_service.wrap(
                    ok=bool(result.get("ok")),
                    mode="runtime_cleanup_run",
                    message="runtime 清理已完成。",
                    data=result,
                    error=result.get("error") if not result.get("ok") else None,
                    previous_state=TaskState.VALIDATED if result.get("ok") else TaskState.FAILED,
                )
            )
            return 0 if result.get("ok") else 1

        if args.runtime_cleanup_command == "schedule-hint":
            result = runtime_cleanup.build_windows_schedule_hint(
                repo_root=args.repo_root,
                at_time=args.time,
                task_name=args.task_name,
            )
            _print_json(
                envelope_service.wrap(
                    ok=True,
                    mode="runtime_cleanup_schedule_hint",
                    message="排程建議已產生。",
                    data=result,
                    previous_state=TaskState.RUNNING,
                )
            )
            return 0

    if args.command == "health":
        if args.health_command == "report":
            result = health_report.report(
                repo_root=args.repo_root,
                refresh_benchmark=bool(args.refresh_benchmark),
                threshold=float(args.threshold),
                save=not bool(args.no_save),
            )
            _print_json(
                envelope_service.wrap(
                    ok=bool(result.get("ok")),
                    mode="health_report",
                    message="健康報告已產生。",
                    data=result,
                    error=result.get("error") if not result.get("ok") else None,
                    previous_state=TaskState.VALIDATED if result.get("ok") else TaskState.FAILED,
                )
            )
            return 0 if result.get("ok") else 1

        if args.health_command == "history":
            result = health_report.history(repo_root=args.repo_root, limit=args.limit)
            _print_json(
                envelope_service.wrap(
                    ok=bool(result.get("ok")),
                    mode="health_history",
                    message="健康歷史已取得。",
                    data=result,
                    error=result.get("error") if not result.get("ok") else None,
                    previous_state=TaskState.RUNNING,
                )
            )
            return 0 if result.get("ok") else 1

        if args.health_command == "schedule-hint":
            result = health_report.build_windows_schedule_hint(
                repo_root=args.repo_root,
                at_time=args.time,
                task_name=args.task_name,
                refresh_benchmark=bool(args.refresh_benchmark),
            )
            _print_json(
                envelope_service.wrap(
                    ok=True,
                    mode="health_schedule_hint",
                    message="健康排程建議已產生。",
                    data=result,
                    previous_state=TaskState.RUNNING,
                )
            )
            return 0

    if args.command == "ops":
        if args.ops_command == "preflight":
            result = ops.preflight(
                repo_root=args.repo_root,
                continue_source_config=args.continue_source_config,
                continue_target_config=args.continue_target_config,
            )
            _print_json(
                envelope_service.wrap(
                    ok=bool(result.get("ok")),
                    mode="ops_preflight",
                    message="preflight 已完成。",
                    data=result,
                    error=result.get("error") if not result.get("ok") else None,
                    previous_state=TaskState.VALIDATED if result.get("ok") else TaskState.FAILED,
                )
            )
            return 0 if result.get("ok") else 1

        if args.ops_command == "daily":
            result = ops.daily(repo_root=args.repo_root, refresh_benchmark=bool(args.refresh_benchmark))
            _print_json(
                envelope_service.wrap(
                    ok=bool(result.get("ok")),
                    mode="ops_daily",
                    message="daily 已完成。",
                    data=result,
                    error=result.get("error") if not result.get("ok") else None,
                    previous_state=TaskState.VALIDATED if result.get("ok") else TaskState.FAILED,
                )
            )
            return 0 if result.get("ok") else 1

        if args.ops_command == "snapshot":
            result = ops.snapshot(repo_root=args.repo_root, tag=args.tag)
            _print_json(
                envelope_service.wrap(
                    ok=bool(result.get("ok")),
                    mode="ops_snapshot",
                    message="ops snapshot 已完成。",
                    data=result,
                    error=result.get("error") if not result.get("ok") else None,
                    previous_state=TaskState.VALIDATED if result.get("ok") else TaskState.FAILED,
                )
            )
            return 0 if result.get("ok") else 1

        if args.ops_command == "run":
            result = ops.run(
                repo_root=args.repo_root,
                profile=args.profile,
                continue_source_config=args.continue_source_config,
                continue_target_config=args.continue_target_config,
                refresh_benchmark=bool(args.refresh_benchmark),
                snapshot_tag=args.snapshot_tag,
            )
            _print_json(
                envelope_service.wrap(
                    ok=bool(result.get("ok")),
                    mode="ops_run",
                    message="ops run 已完成。" if result.get("ok") else "ops run 失敗。",
                    data=result,
                    error=result.get("error") if not result.get("ok") else None,
                    previous_state=TaskState.VALIDATED if result.get("ok") else TaskState.FAILED,
                )
            )
            return 0 if result.get("ok") else 1

    metadata = {"skill": args.skill} if getattr(args, "skill", None) else {}
    ctx = service.build_context(
        repo_root=args.repo_root,
        user_request=args.prompt,
        task_type=args.task_type,
        relative_path=args.relative_path,
        content=args.content,
        mode=args.mode,
        old_text=args.old_text,
        operations=_parse_operations(args.operations_json),
        session_id=args.session_id,
        metadata=metadata,
    )

    if args.command == "plan":
        plan = service.create_plan(ctx)
        _print_json(
            envelope_service.wrap(
                ok=True,
                mode="plan",
                message="計畫已產生。",
                data=plan,
                previous_state=TaskState.PLANNED,
            )
        )
        return 0

    result = service.run(ctx)
    _print_json(
        envelope_service.wrap(
            ok=bool(result.get("ok")),
            mode="run",
            message="任務已完成。" if result.get("ok") else "任務執行失敗。",
            data=result,
            error=result.get("error") if not result.get("ok") else None,
            previous_state=TaskState.RUNNING,
        )
    )
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())

