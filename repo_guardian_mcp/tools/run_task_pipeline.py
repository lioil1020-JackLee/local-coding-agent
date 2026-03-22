from __future__ import annotations

"""run_task_pipeline 工具。"""

import hashlib
import json
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from repo_guardian_mcp.services.response_quality_gate_service import ResponseQualityGateService
from repo_guardian_mcp.services.pipeline_background_service import PipelineBackgroundService
from repo_guardian_mcp.services.task_orchestrator import TaskOrchestrator
from repo_guardian_mcp.services.truthfulness_guard_service import TruthfulnessGuardService
from repo_guardian_mcp.services.user_preference_memory_service import UserPreferenceMemoryService


def run_task_pipeline(
    repo_root: str,
    relative_path: str = "README.md",
    content: str = "",
    mode: str = "append",
    old_text: Optional[str] = None,
    operations: Optional[List[dict[str, Any]]] = None,
    task_type: str = "edit",
    user_request: str = "",
    session_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    auto_decompose: bool = True,
    pipeline_id: str | None = None,
    resume: bool = True,
    max_retries_per_step: int = 1,
    background: bool = False,
) -> Dict[str, Any]:
    start_time = time.time()
    pref_service = UserPreferenceMemoryService()
    quality_service = ResponseQualityGateService()
    truth_service = TruthfulnessGuardService()
    profile = pref_service.update_from_user_request(repo_root=repo_root, user_request=user_request)
    style_hint = pref_service.build_style_hint(profile=profile)

    merged_metadata = {
        **dict(metadata or {}),
        "user_preferences": profile,
        "style_hint": style_hint,
    }

    if background:
        bg = PipelineBackgroundService()
        queued = bg.submit(
            repo_root=repo_root,
            payload={
                "relative_path": relative_path,
                "content": content,
                "mode": mode,
                "old_text": old_text,
                "operations": operations,
                "task_type": task_type,
                "user_request": user_request,
                "session_id": session_id,
                "metadata": merged_metadata,
                "auto_decompose": auto_decompose,
                "pipeline_id": pipeline_id,
                "resume": resume,
                "max_retries_per_step": max_retries_per_step,
            },
        )
        return {
            "ok": True,
            "pipeline": "repo_guardian_task_pipeline",
            "background": True,
            "background_job": queued,
            "preference_profile": profile,
            "summary": "已改為背景執行，完成後可查詢任務狀態。",
            "next_actions": [
                f"請查詢 job 狀態：repo_guardian_pipeline_job_status_tool(repo_root, job_id='{queued['job_id']}')",
            ],
        }

    try:
        orchestrator = TaskOrchestrator()

        if _should_auto_decompose(
            task_type=task_type,
            user_request=user_request,
            content=content,
            operations=operations,
            auto_decompose=auto_decompose,
        ):
            return _run_decomposed_pipeline(
                orchestrator=orchestrator,
                repo_root=repo_root,
                user_request=user_request,
                session_id=session_id,
                metadata=merged_metadata,
                start_time=start_time,
                pipeline_id=pipeline_id,
                resume=resume,
                max_retries_per_step=max_retries_per_step,
                profile=profile,
                style_hint=style_hint,
                quality_service=quality_service,
                truth_service=truth_service,
            )

        orchestrator_start = time.time()
        result = orchestrator.run(
            repo_root=repo_root,
            relative_path=relative_path,
            content=content,
            mode=mode,
            old_text=old_text,
            operations=operations,
            task_type=task_type,
            user_request=user_request,
            session_id=session_id,
            metadata=merged_metadata,
        )
        orchestrator_seconds = round(time.time() - orchestrator_start, 3)
        total_seconds = round(time.time() - start_time, 3)

        if not isinstance(result, dict):
            failed = {
                "ok": False,
                "pipeline": "repo_guardian_task_pipeline",
                "error": "TaskOrchestrator.run() 回傳格式錯誤",
                "timing": {"orchestrator_seconds": orchestrator_seconds, "total_seconds": total_seconds},
                "preference_profile": profile,
            }
            return truth_service.enforce(user_request=user_request, payload=failed)

        quality_review = quality_service.evaluate(user_request=user_request, payload=result, profile=profile)

        output = {
            "pipeline": "repo_guardian_task_pipeline",
            **result,
            "preference_profile": profile,
            "quality_review": quality_review,
            "timing": {"orchestrator_seconds": orchestrator_seconds, "total_seconds": total_seconds},
        }
        return truth_service.enforce(user_request=user_request, payload=output)

    except Exception as exc:  # noqa: BLE001
        total_seconds = round(time.time() - start_time, 3)
        failed = {
            "ok": False,
            "pipeline": "repo_guardian_task_pipeline",
            "error": str(exc),
            "preference_profile": profile,
            "timing": {"total_seconds": total_seconds},
        }
        return truth_service.enforce(user_request=user_request, payload=failed)


def _should_auto_decompose(
    *,
    task_type: str,
    user_request: str,
    content: str,
    operations: Optional[List[dict[str, Any]]],
    auto_decompose: bool,
) -> bool:
    if not auto_decompose:
        return False
    if task_type not in {"auto", "agent", "analyze"}:
        return False
    if content.strip() or (operations and len(operations) > 0):
        return False
    text = (user_request or "").strip()
    if not text:
        return False

    broad_keywords = (
        "整個",
        "全部",
        "完整",
        "從頭到尾",
        "一次",
        "專案在幹嘛",
        "專案在做什麼",
        "目前完成度",
    )
    if any(keyword in text for keyword in broad_keywords):
        return True
    return len(text) >= 24 and ("專案" in text or "repo" in text.lower())


def _build_decomposition_steps(user_request: str, *, style_hint: str) -> list[dict[str, str]]:
    suffix = f"\n{style_hint}" if style_hint else ""
    return [
        {
            "id": "overview",
            "goal": "先建立整體理解",
            "request": (
                f"{user_request}\n請先用白話說明：這個專案是做什麼、給誰用、主要流程是什麼。{suffix}"
            ).strip(),
        },
        {
            "id": "entrypoints",
            "goal": "找出實際入口與核心檔案",
            "request": (f"請根據實際程式碼找出入口檔、核心模組、關鍵呼叫關係，不要只看 README。{suffix}").strip(),
        },
        {
            "id": "capabilities",
            "goal": "整理功能邊界與現況",
            "request": (f"請整理目前已完成功能、未完成功能、風險點，並說明依據來自哪些程式檔。{suffix}").strip(),
        },
        {
            "id": "completion",
            "goal": "給出完成度估算與下一步",
            "request": (f"請根據程式碼證據給完成度百分比（估算）與下一步 3 個建議，白話說明。{suffix}").strip(),
        },
    ]


def _run_decomposed_pipeline(
    *,
    orchestrator: TaskOrchestrator,
    repo_root: str,
    user_request: str,
    session_id: str | None,
    metadata: dict[str, Any] | None,
    start_time: float,
    pipeline_id: str | None,
    resume: bool,
    max_retries_per_step: int,
    profile: dict[str, Any],
    style_hint: str,
    quality_service: ResponseQualityGateService,
    truth_service: TruthfulnessGuardService,
) -> Dict[str, Any]:
    steps = _build_decomposition_steps(user_request, style_hint=style_hint)
    safe_retries = max(0, min(int(max_retries_per_step), 5))
    request_fingerprint = _request_fingerprint(repo_root=repo_root, user_request=user_request)

    auto_resume_selected = False
    real_pipeline_id = (pipeline_id or "").strip()
    if resume and not real_pipeline_id:
        candidate = _find_resumable_pipeline_id(repo_root=repo_root, request_fingerprint=request_fingerprint)
        if candidate:
            real_pipeline_id = candidate
            auto_resume_selected = True
    if not real_pipeline_id:
        real_pipeline_id = f"pipe-{uuid.uuid4().hex[:12]}"

    state = _load_pipeline_state(repo_root=repo_root, pipeline_id=real_pipeline_id) if resume else None
    step_results: list[dict[str, Any]] = list((state or {}).get("step_results") or [])
    failed_step_id: str | None = None
    completed_ids = {str(item.get("id")) for item in step_results if item.get("ok")}

    start_index = 0
    for idx, step in enumerate(steps):
        if step["id"] not in completed_ids:
            start_index = idx
            break
    else:
        start_index = len(steps)

    for index, step in enumerate(steps[start_index:], start=start_index + 1):
        attempt_results: list[dict[str, Any]] = []
        success_payload: dict[str, Any] | None = None
        success_seconds = 0.0
        for attempt in range(1, safe_retries + 2):
            step_start = time.time()
            payload = orchestrator.run(
                repo_root=repo_root,
                task_type="analyze",
                user_request=step["request"],
                session_id=session_id,
                metadata={
                    **dict(metadata or {}),
                    "auto_decomposed": True,
                    "pipeline_id": real_pipeline_id,
                    "pipeline_step_id": step["id"],
                    "pipeline_step_index": index,
                    "pipeline_step_goal": step["goal"],
                    "pipeline_retry_attempt": attempt,
                },
            )
            step_seconds = round(time.time() - step_start, 3)
            ok = bool(payload.get("ok"))
            attempt_results.append(
                {"attempt": attempt, "ok": ok, "duration_seconds": step_seconds, "result": payload}
            )
            if ok:
                success_payload = payload
                success_seconds = step_seconds
                break

        if success_payload is not None:
            step_results.append(
                {
                    "id": step["id"],
                    "goal": step["goal"],
                    "request": step["request"],
                    "ok": True,
                    "duration_seconds": success_seconds,
                    "attempts": attempt_results,
                    "result": success_payload,
                }
            )
            _save_pipeline_state(
                repo_root=repo_root,
                pipeline_id=real_pipeline_id,
                payload={
                    "pipeline_id": real_pipeline_id,
                    "status": "running",
                    "user_request": user_request,
                    "request_fingerprint": request_fingerprint,
                    "completed_steps": len([item for item in step_results if item.get("ok")]),
                    "total_steps": len(steps),
                    "step_results": step_results,
                    "updated_at_ms": int(time.time() * 1000),
                },
            )
            continue

        failed_step_id = step["id"]
        step_results.append(
            {
                "id": step["id"],
                "goal": step["goal"],
                "request": step["request"],
                "ok": False,
                "duration_seconds": sum(float(item["duration_seconds"]) for item in attempt_results),
                "attempts": attempt_results,
                "result": (attempt_results[-1]["result"] if attempt_results else {"ok": False, "error": "unknown"}),
            }
        )
        _save_pipeline_state(
            repo_root=repo_root,
            pipeline_id=real_pipeline_id,
            payload={
                "pipeline_id": real_pipeline_id,
                "status": "failed",
                "failed_step_id": failed_step_id,
                "user_request": user_request,
                "request_fingerprint": request_fingerprint,
                "completed_steps": len([item for item in step_results if item.get("ok")]),
                "total_steps": len(steps),
                "step_results": step_results,
                "updated_at_ms": int(time.time() * 1000),
            },
        )
        break

    total_seconds = round(time.time() - start_time, 3)
    all_ok = failed_step_id is None
    final_step = step_results[-1] if step_results else {}
    final_result = final_step.get("result") if isinstance(final_step, dict) else {"ok": False, "error": "no_step_executed"}
    quality_review = quality_service.evaluate(user_request=user_request, payload=final_result, profile=profile)

    if all_ok and not quality_review.get("passed"):
        review_step_start = time.time()
        repair_request = quality_service.build_repair_request(
            original_request=user_request,
            quality_report=quality_review,
            style_hint=style_hint,
        )
        repair_payload = orchestrator.run(
            repo_root=repo_root,
            task_type="analyze",
            user_request=repair_request,
            session_id=session_id,
            metadata={
                **dict(metadata or {}),
                "auto_decomposed": True,
                "pipeline_id": real_pipeline_id,
                "pipeline_step_id": "self_review_rewrite",
                "pipeline_step_index": len(steps) + 1,
                "pipeline_step_goal": "自我審查重整回覆",
            },
        )
        review_seconds = round(time.time() - review_step_start, 3)
        step_results.append(
            {
                "id": "self_review_rewrite",
                "goal": "自我審查重整回覆",
                "request": repair_request,
                "ok": bool(repair_payload.get("ok")),
                "duration_seconds": review_seconds,
                "attempts": [
                    {
                        "attempt": 1,
                        "ok": bool(repair_payload.get("ok")),
                        "duration_seconds": review_seconds,
                        "result": repair_payload,
                    }
                ],
                "result": repair_payload,
            }
        )
        if repair_payload.get("ok"):
            final_result = repair_payload
            quality_review = quality_service.evaluate(user_request=user_request, payload=final_result, profile=profile)

    _save_pipeline_state(
        repo_root=repo_root,
        pipeline_id=real_pipeline_id,
        payload={
            "pipeline_id": real_pipeline_id,
            "status": "completed" if all_ok else "failed",
            "failed_step_id": failed_step_id,
            "user_request": user_request,
            "request_fingerprint": request_fingerprint,
            "completed_steps": len([item for item in step_results if item.get("ok")]),
            "total_steps": len(steps),
            "step_results": step_results,
            "updated_at_ms": int(time.time() * 1000),
        },
    )

    output = {
        "ok": all_ok,
        "pipeline": "repo_guardian_task_pipeline",
        "pipeline_id": real_pipeline_id,
        "auto_decomposed": True,
        "auto_resume_selected": auto_resume_selected,
        "resumed_from_checkpoint": bool(state),
        "remaining_steps": max(0, len(steps) - len([item for item in step_results if item.get("ok")])),
        "decomposition_plan": [{"id": item["id"], "goal": item["goal"]} for item in steps],
        "completed_steps": len(step_results),
        "failed_step_id": failed_step_id,
        "step_results": step_results,
        "final_result": final_result,
        "preference_profile": profile,
        "quality_review": quality_review,
        "summary": (
            "已自動拆成多步驟並連續執行完成。"
            if all_ok
            else f"自動拆解執行中斷於步驟：{failed_step_id}，可用同一個 pipeline_id 繼續。"
        ),
        "next_actions": (
            ["可直接進入下一階段任務。"]
            if all_ok
            else [f"重試時帶入 pipeline_id={real_pipeline_id} 並設定 resume=true。"]
        ),
        "timing": {
            "orchestrator_seconds": round(sum(item["duration_seconds"] for item in step_results), 3),
            "total_seconds": total_seconds,
        },
    }
    return truth_service.enforce(user_request=user_request, payload=output)


def _pipelines_dir(repo_root: str) -> Path:
    path = Path(repo_root).resolve() / "agent_runtime" / "pipelines"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _pipeline_file(repo_root: str, pipeline_id: str) -> Path:
    return _pipelines_dir(repo_root) / f"{pipeline_id}.json"


def _load_pipeline_state(*, repo_root: str, pipeline_id: str) -> dict[str, Any] | None:
    path = _pipeline_file(repo_root, pipeline_id)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _save_pipeline_state(*, repo_root: str, pipeline_id: str, payload: dict[str, Any]) -> None:
    path = _pipeline_file(repo_root, pipeline_id)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _request_fingerprint(*, repo_root: str, user_request: str) -> str:
    normalized = " ".join((user_request or "").strip().lower().split())
    raw = f"{Path(repo_root).resolve()}||{normalized}".encode("utf-8")
    return hashlib.sha1(raw).hexdigest()


def _find_resumable_pipeline_id(*, repo_root: str, request_fingerprint: str) -> str | None:
    candidates: list[tuple[float, str]] = []
    for path in _pipelines_dir(repo_root).glob("*.json"):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if str(payload.get("request_fingerprint") or "") != request_fingerprint:
            continue
        status = str(payload.get("status") or "")
        completed = int(payload.get("completed_steps") or 0)
        total = int(payload.get("total_steps") or 0)
        if status == "completed" and completed >= total > 0:
            continue
        if status not in {"running", "failed", "completed"}:
            continue
        updated_ms = float(payload.get("updated_at_ms") or 0)
        candidates.append((updated_ms, path.stem))

    if not candidates:
        return None
    candidates.sort(reverse=True)
    return candidates[0][1]
