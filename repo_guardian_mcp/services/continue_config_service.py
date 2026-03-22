from __future__ import annotations

import hashlib
import os
import shutil
import time
from pathlib import Path
from typing import Any


class ContinueConfigService:
    """管理 Continue 設定檔比對與同步。"""

    TARGET_PROFILE_PATHS = {
        "cursor": ".continue/config.yaml",
        "continue-default": ".continue/config.yaml",
    }

    def _sha256(self, path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as fh:
            for chunk in iter(lambda: fh.read(65536), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def status(self, *, source_config: str, target_config: str) -> dict:
        source = Path(source_config).resolve()
        target = Path(target_config).resolve()

        source_exists = source.exists()
        target_exists = target.exists()
        same = False
        source_hash = None
        target_hash = None

        if source_exists:
            source_hash = self._sha256(source)
        if target_exists:
            target_hash = self._sha256(target)
        if source_hash and target_hash:
            same = source_hash == target_hash

        return {
            "ok": source_exists,
            "source_config": str(source),
            "target_config": str(target),
            "source_exists": source_exists,
            "target_exists": target_exists,
            "same_content": same,
            "source_sha256": source_hash,
            "target_sha256": target_hash,
            "message": "設定一致" if same else "設定不一致或尚未同步",
            "next_actions": (
                ["可直接使用，暫不需同步。"]
                if same
                else ["請執行 continue-config sync 同步設定。"]
            ),
            "error": None if source_exists else f"找不到來源設定檔: {source}",
        }

    def sync(
        self,
        *,
        source_config: str,
        target_config: str,
        with_assets: bool = False,
    ) -> dict:
        source = Path(source_config).resolve()
        target = Path(target_config).resolve()
        if not source.exists():
            return {
                "ok": False,
                "source_config": str(source),
                "target_config": str(target),
                "error": f"找不到來源設定檔: {source}",
            }

        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)

        copied_assets: list[str] = []
        if with_assets:
            source_root = source.parent
            target_root = target.parent
            for name in ("rules", "system-prompts"):
                src_dir = source_root / name
                dst_dir = target_root / name
                if not src_dir.exists():
                    continue
                if dst_dir.exists():
                    shutil.rmtree(dst_dir)
                shutil.copytree(src_dir, dst_dir)
                copied_assets.append(name)

        status = self.status(source_config=str(source), target_config=str(target))
        return {
            "ok": bool(status.get("same_content")),
            "source_config": str(source),
            "target_config": str(target),
            "with_assets": with_assets,
            "copied_assets": copied_assets,
            "same_content": status.get("same_content"),
            "source_sha256": status.get("source_sha256"),
            "target_sha256": status.get("target_sha256"),
            "message": "Continue 設定已同步。",
        }

    def _resolve_source_config(self, *, repo_root: Path, source_config: str) -> Path:
        source = Path(source_config)
        if source.is_absolute():
            return source.resolve()
        return (repo_root / source).resolve()

    def _resolve_target_config(self, *, target_config: str | None, target_profile: str) -> Path:
        if target_config:
            return Path(target_config).expanduser().resolve()

        profile = (target_profile or "cursor").strip().lower()
        profile_path = self.TARGET_PROFILE_PATHS.get(profile)
        if not profile_path:
            allowed = ", ".join(sorted(self.TARGET_PROFILE_PATHS))
            raise ValueError(f"不支援的 target_profile: {profile}，可用值: {allowed}")
        return (Path.home() / profile_path).resolve()

    def _safe_copy_backup(self, *, source: Path, target: Path) -> str:
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            shutil.copytree(source, target, dirs_exist_ok=False)
        else:
            shutil.copy2(source, target)
        return str(target)

    def _copy_path(self, *, source: Path, target: Path) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            shutil.copytree(source, target, dirs_exist_ok=False)
        else:
            shutil.copy2(source, target)

    def _remove_path(self, path: Path) -> None:
        if not path.exists():
            return
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()

    def _classify_error(self, exc: Exception, *, phase: str) -> str:
        if isinstance(exc, PermissionError):
            return "permission_denied"
        if isinstance(exc, FileNotFoundError):
            return "path_not_found"
        if isinstance(exc, ValueError):
            return "invalid_argument"
        if phase == "sync":
            return "sync_failed"
        if phase == "diagnose":
            return "diagnose_failed"
        if phase == "backup":
            return "backup_failed"
        return "setup_exception"

    def _attempt_restore(
        self,
        *,
        states: dict[str, dict[str, Any]],
        backups: dict[str, Path],
    ) -> dict[str, Any]:
        restored: list[str] = []
        removed_new: list[str] = []
        errors: list[str] = []

        for key, item in states.items():
            path = item["path"]
            existed_before = bool(item["existed_before"])
            backup_path = backups.get(key)
            try:
                if existed_before:
                    if not backup_path or not backup_path.exists():
                        errors.append(f"{key}: 缺少備份，無法還原")
                        continue
                    self._remove_path(path)
                    self._copy_path(source=backup_path, target=path)
                    restored.append(str(path))
                else:
                    if path.exists():
                        self._remove_path(path)
                        removed_new.append(str(path))
            except Exception as rollback_exc:  # noqa: BLE001
                errors.append(f"{key}: {rollback_exc}")

        return {
            "attempted": True,
            "performed": len(errors) == 0,
            "restored": restored,
            "removed_new": removed_new,
            "errors": errors,
        }

    def _count_files(self, path: Path) -> int:
        if not path.exists() or not path.is_dir():
            return 0
        count = 0
        try:
            for item in path.rglob("*"):
                if item.is_file():
                    count += 1
        except OSError:
            return count
        return count

    def _asset_state(self, config_path: Path) -> dict[str, Any]:
        root = config_path.parent
        rules_dir = root / "rules"
        prompts_dir = root / "system-prompts"
        return {
            "root": str(root),
            "rules_exists": rules_dir.exists(),
            "system_prompts_exists": prompts_dir.exists(),
            "rules_file_count": self._count_files(rules_dir),
            "system_prompts_file_count": self._count_files(prompts_dir),
        }

    def _diagnosis_score(self, checks: list[dict[str, Any]]) -> int:
        score = 100
        for item in checks:
            if item.get("ok", False):
                continue
            severity = str(item.get("severity") or "warning")
            if severity == "blocker":
                score -= 40
            elif severity == "warning":
                score -= 15
            else:
                score -= 5
        return max(0, min(100, score))

    def diagnose(
        self,
        *,
        repo_root: str,
        source_config: str = "continue/config.yaml",
        target_config: str | None = None,
        target_profile: str = "cursor",
        with_assets: bool = True,
    ) -> dict[str, Any]:
        root = Path(repo_root).resolve()
        try:
            source = self._resolve_source_config(repo_root=root, source_config=source_config)
            target = self._resolve_target_config(target_config=target_config, target_profile=target_profile)
        except ValueError as exc:
            return {
                "ok": False,
                "ready": False,
                "repo_root": str(root),
                "error": str(exc),
                "checks": [],
                "repair_hints": ["請修正 target_profile，或直接指定 --target-config。"],
                "recommended_commands": [],
            }

        status = self.status(source_config=str(source), target_config=str(target))
        source_assets = self._asset_state(source)
        target_assets = self._asset_state(target)

        checks: list[dict[str, Any]] = []

        def add_check(
            *,
            name: str,
            ok: bool,
            severity: str,
            message: str,
            repair_hint: str | None = None,
            command: str | None = None,
        ) -> None:
            checks.append(
                {
                    "name": name,
                    "ok": ok,
                    "severity": severity,
                    "message": message,
                    "repair_hint": repair_hint,
                    "recommended_command": command,
                }
            )

        add_check(
            name="source_config_exists",
            ok=bool(status.get("source_exists")),
            severity="blocker",
            message="找到來源設定檔。" if status.get("source_exists") else "找不到來源設定檔。",
            repair_hint="請確認 repo 裡有 continue/config.yaml。",
        )
        add_check(
            name="target_config_exists",
            ok=bool(status.get("target_exists")),
            severity="warning",
            message="找到目標設定檔。" if status.get("target_exists") else "目標設定檔尚未建立。",
            repair_hint="先執行 continue-config setup 建立目標設定。",
            command=f'uv run repo-guardian continue-config setup "{root}" --target-config "{target}"',
        )
        add_check(
            name="config_content_synced",
            ok=bool(status.get("same_content")),
            severity="warning",
            message="來源與目標設定內容一致。" if status.get("same_content") else "來源與目標設定內容不一致。",
            repair_hint="重新執行 setup 或 sync 同步設定。",
            command=f'uv run repo-guardian continue-config setup "{root}" --target-config "{target}"',
        )

        if with_assets:
            for asset_name, source_count_key, target_count_key in (
                ("rules", "rules_file_count", "rules_file_count"),
                ("system-prompts", "system_prompts_file_count", "system_prompts_file_count"),
            ):
                source_count = int(source_assets.get(source_count_key) or 0)
                target_count = int(target_assets.get(target_count_key) or 0)
                has_source_asset = source_count > 0
                if has_source_asset:
                    add_check(
                        name=f"{asset_name}_synced",
                        ok=target_count > 0,
                        severity="warning",
                        message=(
                            f"{asset_name} 已同步。"
                            if target_count > 0
                            else f"{asset_name} 尚未同步到目標。"
                        ),
                        repair_hint=f"重新執行 setup 並保留 assets 同步（不要加 --without-assets）。",
                        command=(
                            f'uv run repo-guardian continue-config setup "{root}" '
                            f'--target-config "{target}"'
                        ),
                    )
                else:
                    add_check(
                        name=f"{asset_name}_source_missing",
                        ok=True,
                        severity="info",
                        message=f"來源中沒有 {asset_name}，本次不要求同步。",
                    )

        target_parent = target.parent
        writable_parent = target_parent if target_parent.exists() else target_parent.parent
        add_check(
            name="target_directory_writable",
            ok=bool(os.access(writable_parent, os.W_OK)),
            severity="blocker",
            message="目標資料夾可寫入。" if os.access(writable_parent, os.W_OK) else "目標資料夾可能無法寫入。",
            repair_hint="請改用有寫入權限的目標路徑，或調整資料夾權限。",
        )

        blocker_failed = any((not item.get("ok")) and item.get("severity") == "blocker" for item in checks)
        warning_failed = any((not item.get("ok")) and item.get("severity") == "warning" for item in checks)
        score = self._diagnosis_score(checks)
        repair_hints = [str(item["repair_hint"]) for item in checks if (not item.get("ok")) and item.get("repair_hint")]
        # 去重但保留順序
        repair_hints = list(dict.fromkeys(repair_hints))
        commands = [str(item["recommended_command"]) for item in checks if (not item.get("ok")) and item.get("recommended_command")]
        commands = list(dict.fromkeys(commands))

        ready = (not blocker_failed) and (not warning_failed)
        ok = not blocker_failed
        return {
            "ok": ok,
            "ready": ready,
            "score": score,
            "repo_root": str(root),
            "source_config": str(source),
            "target_config": str(target),
            "target_profile": target_profile,
            "with_assets": with_assets,
            "status": status,
            "source_assets": source_assets,
            "target_assets": target_assets,
            "checks": checks,
            "repair_hints": repair_hints,
            "recommended_commands": commands,
            "user_friendly_summary": (
                "Continue/Cursor 設定已可用。"
                if ready
                else "我找到幾個可修正項目，修完會更穩定。"
            ),
            "next_actions": (
                ["可直接進入開發，若要保險可再跑 continue-e2e。"]
                if ready
                else repair_hints[:3] or ["先重跑 continue-config setup。"]
            ),
        }

    def setup(
        self,
        *,
        repo_root: str,
        source_config: str = "continue/config.yaml",
        target_config: str | None = None,
        target_profile: str = "cursor",
        with_assets: bool = True,
        backup: bool = True,
        dry_run: bool = False,
        run_e2e: bool = False,
    ) -> dict[str, Any]:
        root = Path(repo_root).resolve()
        phase = "resolve"
        try:
            source = self._resolve_source_config(repo_root=root, source_config=source_config)
            target = self._resolve_target_config(target_config=target_config, target_profile=target_profile)
        except ValueError as exc:
            return {
                "ok": False,
                "repo_root": str(root),
                "error_code": "invalid_argument",
                "error_phase": phase,
                "error": str(exc),
                "next_actions": ["請改用支援的 target_profile，或直接指定 --target-config。"],
            }

        before = self.status(source_config=str(source), target_config=str(target))
        if not before.get("ok"):
            return {
                "ok": False,
                "repo_root": str(root),
                "source_config": str(source),
                "target_config": str(target),
                "target_profile": target_profile,
                "status_before": before,
                "error_code": "source_missing",
                "error_phase": "precheck",
                "error": before.get("error"),
                "user_friendly_summary": "找不到 Continue 來源設定檔，尚未完成 setup。",
                "next_actions": ["請先確認 repo 內有 continue/config.yaml。"],
            }

        if dry_run:
            diagnosis = self.diagnose(
                repo_root=str(root),
                source_config=str(source),
                target_config=str(target),
                target_profile=target_profile,
                with_assets=with_assets,
            )
            return {
                "ok": True,
                "repo_root": str(root),
                "source_config": str(source),
                "target_config": str(target),
                "target_profile": target_profile,
                "with_assets": with_assets,
                "backup": backup,
                "dry_run": True,
                "run_e2e": run_e2e,
                "ready": bool(diagnosis.get("ready")),
                "status_before": before,
                "status_after": before,
                "diagnosis": diagnosis,
                "backups": [],
                "message": "setup dry-run 完成，尚未變更任何檔案。",
                "user_friendly_summary": "我已完成 setup 預檢（dry-run），目前還沒有寫入任何設定。",
                "next_actions": ["確認路徑後，移除 --dry-run 重新執行 setup。"],
            }

        timestamp = int(time.time() * 1000)
        backup_root = target.parent / "backups"
        backup_items: list[str] = []
        backup_paths: dict[str, Path] = {}
        target_states: dict[str, dict[str, Any]] = {
            "config": {
                "path": target,
                "existed_before": target.exists(),
            }
        }
        if with_assets:
            for name in ("rules", "system-prompts"):
                target_states[name] = {
                    "path": target.parent / name,
                    "existed_before": (target.parent / name).exists(),
                }

        try:
            phase = "backup"
            if backup:
                for key, state in target_states.items():
                    existing_path: Path = state["path"]
                    if not existing_path.exists():
                        continue
                    backup_name = existing_path.name if key == "config" else key
                    backup_path = backup_root / f"{backup_name}.bak-{timestamp}"
                    self._safe_copy_backup(source=existing_path, target=backup_path)
                    backup_paths[key] = backup_path
                    backup_items.append(str(backup_path))

            phase = "sync"
            sync_result = self.sync(
                source_config=str(source),
                target_config=str(target),
                with_assets=with_assets,
            )
            phase = "status_after"
            after = self.status(source_config=str(source), target_config=str(target))
            phase = "diagnose"
            diagnosis = self.diagnose(
                repo_root=str(root),
                source_config=str(source),
                target_config=str(target),
                target_profile=target_profile,
                with_assets=with_assets,
            )

            e2e_result: dict[str, Any] | None = None
            e2e_passed = True
            if run_e2e:
                phase = "e2e"
                try:
                    from repo_guardian_mcp.services.continue_e2e_service import ContinueE2EService

                    e2e_result = ContinueE2EService().run(repo_root=str(root))
                    e2e_passed = bool(e2e_result.get("passed"))
                except Exception as e2e_exc:  # noqa: BLE001
                    e2e_result = {"ok": False, "passed": False, "error": str(e2e_exc), "checks": []}
                    e2e_passed = False

            ready = bool(diagnosis.get("ready")) and e2e_passed
            ok = bool(sync_result.get("ok")) and ready
            if (not e2e_passed) and run_e2e:
                next_actions = [
                    "Continue e2e 有失敗步驟，請先查看 e2e.checks 的 error 欄位。",
                    "修正後重跑：uv run repo-guardian continue-config setup . --target-profile cursor --run-e2e",
                ]
            else:
                next_actions = (
                    ["建議重啟 Cursor 或 Continue 擴充後開始使用。"]
                    if ok
                    else (diagnosis.get("next_actions") or ["請先查看 e2e 或設定差異結果，再重跑 setup。"])
                )
            if (not run_e2e) and ready:
                next_actions = list(dict.fromkeys([*next_actions, "可再執行 continue-e2e run . 做最後驗證。"]))
            return {
                "ok": ok,
                "repo_root": str(root),
                "source_config": str(source),
                "target_config": str(target),
                "target_profile": target_profile,
                "with_assets": with_assets,
                "backup": backup,
                "dry_run": False,
                "run_e2e": run_e2e,
                "ready": ready,
                "status_before": before,
                "sync": sync_result,
                "status_after": after,
                "diagnosis": diagnosis,
                "backups": backup_items,
                "rollback": {"attempted": False, "performed": True, "restored": [], "removed_new": [], "errors": []},
                "e2e": e2e_result,
                "message": "Continue setup 完成。" if ok else "Continue setup 完成，但仍有待處理項目。",
                "user_friendly_summary": (
                    "Continue/Cursor 設定已接好，可以直接使用。"
                    if ok
                    else ("設定已寫入，但 Continue e2e 尚未通過。" if (run_e2e and not e2e_passed) else "設定已寫入，但還有檢查項目尚未通過。")
                ),
                "next_actions": next_actions,
                "error_code": None if ok else ("e2e_failed" if (run_e2e and not e2e_passed) else "diagnosis_not_ready"),
                "error_phase": None if ok else ("e2e" if (run_e2e and not e2e_passed) else "diagnose"),
            }
        except Exception as exc:  # noqa: BLE001
            error_code = self._classify_error(exc, phase=phase)
            rollback = {
                "attempted": False,
                "performed": False,
                "restored": [],
                "removed_new": [],
                "errors": [],
            }
            if phase in {"sync", "status_after", "diagnose"}:
                rollback = self._attempt_restore(states=target_states, backups=backup_paths)
            hints = {
                "permission_denied": ["目標路徑權限不足，請改用可寫入目錄或調整權限。"],
                "path_not_found": ["有路徑不存在，請確認 source/target 路徑設定。"],
                "invalid_argument": ["參數格式不正確，請先跑 continue-config diagnose 檢查。"],
                "backup_failed": ["備份階段失敗，請確認目標目錄是否可寫入。"],
                "sync_failed": ["同步階段失敗，建議先用 --dry-run 檢查。"],
                "diagnose_failed": ["同步後診斷失敗，請先手動執行 continue-config diagnose。"],
                "setup_exception": ["setup 發生未分類錯誤，請查看 error 與 rollback 結果。"],
            }
            return {
                "ok": False,
                "repo_root": str(root),
                "source_config": str(source),
                "target_config": str(target),
                "target_profile": target_profile,
                "with_assets": with_assets,
                "backup": backup,
                "dry_run": False,
                "run_e2e": run_e2e,
                "status_before": before,
                "backups": backup_items,
                "rollback": rollback,
                "error_code": error_code,
                "error_phase": phase,
                "error": str(exc),
                "user_friendly_summary": "setup 途中發生錯誤，尚未完成。",
                "next_actions": hints.get(error_code) or ["請先確認目標路徑可寫入，或改用 --target-config 指定其他位置。"],
            }

    def autofix(
        self,
        *,
        repo_root: str,
        source_config: str = "continue/config.yaml",
        target_config: str | None = None,
        target_profile: str = "cursor",
        with_assets: bool = True,
        backup: bool = True,
        dry_run: bool = False,
        run_e2e: bool = False,
    ) -> dict[str, Any]:
        before = self.diagnose(
            repo_root=repo_root,
            source_config=source_config,
            target_config=target_config,
            target_profile=target_profile,
            with_assets=with_assets,
        )
        if not before.get("ok"):
            return {
                "ok": False,
                "ready": False,
                "changed": False,
                "dry_run": dry_run,
                "run_e2e": run_e2e,
                "before": before,
                "after": before,
                "applied_actions": [],
                "error": before.get("error") or "autofix 前置診斷失敗。",
                "user_friendly_summary": "autofix 無法開始，請先修正前置診斷問題。",
                "next_actions": before.get("next_actions") or ["請先修正 blocker，再重跑 autofix。"],
            }

        if before.get("ready"):
            return {
                "ok": True,
                "ready": True,
                "changed": False,
                "dry_run": dry_run,
                "run_e2e": run_e2e,
                "before": before,
                "after": before,
                "applied_actions": [],
                "message": "目前已是可用狀態，autofix 不需要變更。",
                "user_friendly_summary": "目前設定已可用，沒有需要自動修復的項目。",
                "next_actions": ["可直接開始使用，或執行 continue-e2e 進一步確認。"],
            }

        planned_actions = ["continue_config_setup"]
        if dry_run:
            return {
                "ok": True,
                "ready": bool(before.get("ready")),
                "changed": False,
                "dry_run": True,
                "run_e2e": run_e2e,
                "before": before,
                "after": before,
                "applied_actions": [],
                "planned_actions": planned_actions,
                "message": "autofix dry-run 完成，尚未變更任何檔案。",
                "user_friendly_summary": "我已完成 autofix 預檢，已整理出可自動修復的步驟。",
                "next_actions": before.get("next_actions") or ["移除 --dry-run 後重跑 autofix。"],
            }

        setup_result = self.setup(
            repo_root=repo_root,
            source_config=source_config,
            target_config=target_config,
            target_profile=target_profile,
            with_assets=with_assets,
            backup=backup,
            dry_run=False,
            run_e2e=run_e2e,
        )
        after = self.diagnose(
            repo_root=repo_root,
            source_config=source_config,
            target_config=target_config,
            target_profile=target_profile,
            with_assets=with_assets,
        )

        e2e_passed = True
        if run_e2e:
            e2e_passed = bool((setup_result.get("e2e") or {}).get("passed"))
        ready = bool(after.get("ready")) and e2e_passed
        ok = bool(setup_result.get("ok")) and ready
        changed = bool(setup_result.get("sync")) or bool((setup_result.get("rollback") or {}).get("attempted"))
        return {
            "ok": ok,
            "ready": ready,
            "changed": changed,
            "dry_run": False,
            "run_e2e": run_e2e,
            "before": before,
            "after": after,
            "setup": setup_result,
            "applied_actions": planned_actions,
            "message": "autofix 已完成。" if ok else "autofix 已執行，但仍有未完成項目。",
            "user_friendly_summary": (
                "我已完成自動修復，Continue/Cursor 設定可直接使用。"
                if ok
                else "我已嘗試自動修復，但還有項目需要你確認。"
            ),
            "next_actions": (
                ["可直接進入開發。"]
                if ok
                else (
                    (setup_result.get("next_actions") or [])
                    or (after.get("next_actions") or [])
                    or ["請查看 setup / diagnose 結果後再重跑 autofix。"]
                )
            ),
            "error_code": None if ok else (setup_result.get("error_code") or "autofix_incomplete"),
            "error_phase": None if ok else setup_result.get("error_phase"),
        }
