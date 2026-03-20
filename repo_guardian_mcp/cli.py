from __future__ import annotations

import argparse
import contextlib
import json
import os
from pathlib import Path
from typing import Any, Iterator

from repo_guardian_mcp.services.cli_agent_service import CLIAgentService
from repo_guardian_mcp.services.cli_chat_service import CLIChatService
from repo_guardian_mcp.tools.list_sessions import list_sessions_tool
from repo_guardian_mcp.tools.preview_session_diff import preview_session_diff
from repo_guardian_mcp.tools.resume_session import resume_session_tool
from repo_guardian_mcp.tools.rollback_session import rollback_session


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="repo-guardian",
        description="Local CLI coding agent with skill system and safe-edit workflows.",
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

    sub.add_parser("skills", help="列出目前可用 skills")
    sub.add_parser("plan", parents=[common], help="預覽 agent plan")
    sub.add_parser("run", parents=[common], help="執行 agent 任務")

    chat_parser = sub.add_parser("chat", help="進入互動式 chat 模式")
    chat_parser.add_argument("repo_root")
    chat_parser.add_argument("--task-type", default="auto", choices=["auto", "agent", "edit", "analyze"])
    chat_parser.add_argument("--message", default=None, help="單次訊息模式")
    chat_parser.add_argument("--once", action="store_true", help="搭配 --message 使用，處理一次就結束")

    session_parser = sub.add_parser("session", help="session 管理命令")
    session_sub = session_parser.add_subparsers(dest="session_command", required=True)

    session_list = session_sub.add_parser("list", help="列出 session")
    session_list.add_argument("repo_root")
    session_list.add_argument("--include-cleaned", action="store_true")

    session_resume = session_sub.add_parser("resume", help="恢復並 touch 指定 session")
    session_resume.add_argument("repo_root")
    session_resume.add_argument("session_id")

    diff_parser = sub.add_parser("diff", help="預覽指定 session 與 repo 的差異")
    diff_parser.add_argument("repo_root")
    diff_parser.add_argument("session_id")

    rollback_parser = sub.add_parser("rollback", help="回滾指定 session")
    rollback_parser.add_argument("repo_root")
    rollback_parser.add_argument("session_id")
    rollback_parser.add_argument("--keep-workspace", action="store_true", help="回滾後保留 sandbox 工作區")

    return parser


def _parse_operations(raw: str | None) -> list[dict[str, Any]] | None:
    if not raw:
        return None
    value = json.loads(raw)
    if not isinstance(value, list):
        raise ValueError("operations-json 必須是 JSON list")
    return value


def _resolve_sessions_dir(repo_root: str) -> str:
    return str((Path(repo_root).resolve() / "agent_runtime" / "sessions").resolve())


@contextlib.contextmanager
def _pushd(path: str | os.PathLike[str]) -> Iterator[None]:
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


def _run_chat(repo_root: str, task_type: str, message: str | None, once: bool) -> int:
    chat = CLIChatService()
    if message is not None:
        turn = chat.handle_input(repo_root=repo_root, raw_text=message, default_task_type=task_type)
        print(json.dumps({"ok": turn.ok, "mode": turn.mode, "message": turn.message, **turn.payload}, ensure_ascii=False, indent=2))
        return 0 if turn.ok else 1

    print("repo-guardian chat 已啟動。輸入 /help 查看指令，輸入 /exit 結束。")
    while True:
        try:
            raw = input("repo-guardian> ")
        except EOFError:
            print("已結束 chat。")
            return 0
        turn = chat.handle_input(repo_root=repo_root, raw_text=raw, default_task_type=task_type)
        if turn.mode == "noop" and not turn.message:
            if once:
                return 0
            continue
        print(json.dumps({"ok": turn.ok, "mode": turn.mode, "message": turn.message, **turn.payload}, ensure_ascii=False, indent=2))
        if turn.mode == "exit":
            return 0
        if once:
            return 0 if turn.ok else 1


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    service = CLIAgentService()

    if args.command == "skills":
        print(json.dumps({"ok": True, "skills": service.skill_registry.list_skill_metadata()}, ensure_ascii=False, indent=2))
        return 0

    if args.command == "chat":
        return _run_chat(args.repo_root, args.task_type, args.message, args.once)

    if args.command == "session":
        sessions_dir = _resolve_sessions_dir(args.repo_root)
        if args.session_command == "list":
            result = list_sessions_tool(sessions_dir, include_cleaned=args.include_cleaned)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0 if result.get("ok") else 1

        if args.session_command == "resume":
            result = resume_session_tool(sessions_dir, session_id=args.session_id)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0 if result.get("ok") else 1

        parser.error("未知的 session 子命令")
        return 2

    if args.command == "diff":
        with _pushd(args.repo_root):
            result = preview_session_diff(args.session_id)
        if result.get("ok"):
            result = {**result, "changed_file_count": len(result.get("changed_files") or [])}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result.get("ok") else 1

    if args.command == "rollback":
        result = rollback_session(
            repo_root=args.repo_root,
            session_id=args.session_id,
            cleanup_workspace=not args.keep_workspace,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
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
        print(json.dumps(service.create_plan(ctx), ensure_ascii=False, indent=2))
        return 0

    result = service.run(ctx)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
