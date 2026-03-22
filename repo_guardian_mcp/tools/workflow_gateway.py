from __future__ import annotations

from typing import Any

from repo_guardian_mcp.services.cli_agent_service import CLIAgentService
from repo_guardian_mcp.services.edit_execution_orchestrator import EditExecutionOrchestrator
from repo_guardian_mcp.services.intent_resolution_service import IntentResolutionService
from repo_guardian_mcp.services.agent_session_state_service import AgentSessionState
from repo_guardian_mcp.services.plain_language_understanding_service import PlainLanguageUnderstandingService


def preview_user_request_plan(
    repo_root: str,
    user_request: str,
    task_type: str = "auto",
    session_id: str | None = None,
) -> dict[str, Any]:
    """先做白話需求規劃，不修改檔案。"""
    service = CLIAgentService()
    ctx = service.build_context(
        repo_root=repo_root,
        user_request=user_request,
        task_type=task_type,
        session_id=session_id,
        metadata={"source": "workflow_gateway", "plan_only": True},
    )
    plan = service.create_plan(ctx)
    return {
        "ok": True,
        "mode": "plan",
        "user_request": user_request,
        "task_type": task_type,
        "selected_skill": plan.get("selected_skill"),
        "plan": plan,
        "user_friendly_summary": f"我已先幫你排好執行步驟，建議使用「{plan.get('selected_skill')}」流程。",
        "next_actions": ["如果要正式執行，請呼叫 handle_user_request。"],
    }


def handle_user_request(
    repo_root: str,
    user_request: str,
    task_type: str = "auto",
    session_id: str | None = None,
    apply: bool = False,
    relative_path: str | None = None,
    content: str | None = None,
    mode: str | None = None,
    old_text: str | None = None,
    operations: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """高階白話入口：自動判斷分析或修改。"""
    service = CLIAgentService()
    plain = PlainLanguageUnderstandingService().interpret(user_request)
    state = AgentSessionState(session_id="virtual", repo_root=repo_root)
    intent = IntentResolutionService().resolve(user_request, state)
    resolved_task_type = task_type

    if task_type == "auto":
        if intent.intent == "analyze_repo":
            resolved_task_type = "analyze"
        elif intent.intent in {"propose_edit", "apply_edit", "resume_context"}:
            resolved_task_type = "edit"

    ctx = service.build_context(
        repo_root=repo_root,
        user_request=user_request,
        task_type=resolved_task_type,
        relative_path=relative_path or plain.relative_path or "README.md",
        content=content or plain.content or "",
        mode=mode or plain.mode or "append",
        old_text=old_text or plain.old_text,
        operations=operations,
        session_id=session_id,
        metadata={"source": "workflow_gateway", "intent": intent.intent},
    )

    if resolved_task_type == "edit":
        # 修改需求：apply=true 才執行，而且需要足夠資訊。
        if not apply:
            plan = service.create_plan(ctx)
            return {
                "ok": True,
                "mode": "plan",
                "intent": intent.intent,
                "selected_skill": plan.get("selected_skill"),
                "plan": plan,
                "user_friendly_summary": "我先幫你規劃了安全修改步驟，尚未真的改檔。",
                "next_actions": ["若確認要改，請設定 apply=true；或改用 create_task_session + edit_file。"],
            }

        has_structured_edit = bool(operations) or bool(ctx.content and ctx.content.strip())
        if not has_structured_edit and ctx.mode == "replace" and ctx.old_text and ctx.content:
            has_structured_edit = True

        if not has_structured_edit:
            return {
                "ok": False,
                "mode": "run",
                "intent": intent.intent,
                "error": {
                    "code": "user_input_error",
                    "message": "修改資訊不足，請提供 content 或 operations；也可以先用 edit_file 工具。",
                    "hint": "範例：relative_path=README.md, content='新增一行', mode='append'",
                },
                "user_friendly_summary": "我知道你想修改，但目前缺少可執行的修改內容。",
                "next_actions": [
                    "補上 relative_path 與 content 後再呼叫 handle_user_request(apply=true)。",
                    "或改走 create_task_session -> edit_file -> preview_session_diff -> run_validation_pipeline。",
                ],
            }

        orchestrator = EditExecutionOrchestrator()
        if session_id:
            result = orchestrator.edit_existing_session(
                repo_root=repo_root,
                session_id=session_id,
                relative_path=ctx.relative_path,
                content=ctx.content,
                mode=ctx.mode,
                old_text=ctx.old_text,
                operations=ctx.operations,
                read_only=False,
            )
        else:
            result = orchestrator.run(
                repo_root=repo_root,
                relative_path=ctx.relative_path,
                content=ctx.content,
                mode=ctx.mode,
                old_text=ctx.old_text,
                operations=ctx.operations,
                read_only=False,
            )
        return {
            "ok": bool(result.get("ok")),
            "mode": "run",
            "intent": intent.intent,
            **result,
        }

    result = service.run(ctx)
    return {
        "ok": bool(result.get("ok")),
        "mode": "run",
        "intent": intent.intent,
        **result,
    }


def edit_file(
    repo_root: str,
    session_id: str,
    relative_path: str,
    content: str,
    mode: str = "append",
    old_text: str | None = None,
    operations: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """低階安全修改入口：在既有 session 上修改。"""
    orchestrator = EditExecutionOrchestrator()
    result = orchestrator.edit_existing_session(
        repo_root=repo_root,
        session_id=session_id,
        relative_path=relative_path,
        content=content,
        mode=mode,
        old_text=old_text,
        operations=operations,
        read_only=False,
    )
    if not result.get("ok"):
        return {
            "ok": False,
            "mode": "edit",
            **result,
        }
    return {
        "ok": True,
        "mode": "edit",
        **result,
    }
