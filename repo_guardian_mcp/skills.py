from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from repo_guardian_mcp.services.edit_execution_orchestrator import EditExecutionOrchestrator


@dataclass
class SkillContext:
    repo_root: str
    user_request: str = ""
    task_type: str = "auto"
    relative_path: str = "README.md"
    content: str = ""
    mode: str = "append"
    old_text: str | None = None
    operations: list[dict[str, Any]] | None = None
    session_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SkillPlan:
    skill_name: str
    intent: str
    summary: str
    steps: list[str] = field(default_factory=list)
    requires_validation: bool = False
    requires_session: bool = False


@dataclass
class SkillResult:
    ok: bool
    skill_name: str
    output: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    validation: dict[str, Any] = field(default_factory=dict)
    session_id: str | None = None


@dataclass
class SkillMetadata:
    name: str
    description: str
    version: str = "1.0"
    capabilities: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    aliases: list[str] = field(default_factory=list)
    examples: list[str] = field(default_factory=list)
    routing_hints: list[str] = field(default_factory=list)
    requires_session: bool = False
    requires_validation: bool = False
    priority: int = 100
    enabled: bool = True


@runtime_checkable
class Skill(Protocol):
    name: str
    description: str
    metadata: SkillMetadata

    def can_handle(self, ctx: SkillContext) -> bool: ...
    def plan(self, ctx: SkillContext) -> SkillPlan: ...
    def execute(self, ctx: SkillContext, plan: SkillPlan) -> SkillResult: ...
    def validate(self, ctx: SkillContext, result: SkillResult) -> dict[str, Any]: ...


class SkillRegistry:
    def __init__(self, skills: list[Skill] | None = None) -> None:
        self._skills: list[Skill] = []
        for skill in skills or []:
            self.register(skill)

    def register(self, skill: Skill) -> None:
        self._skills.append(skill)
        self._skills.sort(key=lambda item: getattr(item.metadata, "priority", 100))

    def list_skills(self) -> list[Skill]:
        return [skill for skill in self._skills if getattr(skill.metadata, "enabled", True)]

    def list_skill_metadata(self) -> list[dict[str, Any]]:
        data: list[dict[str, Any]] = []
        for skill in self.list_skills():
            data.append(
                {
                    "name": skill.metadata.name,
                    "description": skill.metadata.description,
                    "version": skill.metadata.version,
                    "capabilities": list(skill.metadata.capabilities),
                    "tags": list(skill.metadata.tags),
                    "aliases": list(skill.metadata.aliases),
                    "examples": list(skill.metadata.examples),
                    "routing_hints": list(skill.metadata.routing_hints),
                    "requires_session": skill.metadata.requires_session,
                    "requires_validation": skill.metadata.requires_validation,
                    "priority": skill.metadata.priority,
                    "enabled": skill.metadata.enabled,
                }
            )
        return data

    def get(self, name: str) -> Skill | None:
        wanted = name.strip().lower()
        for skill in self.list_skills():
            names = [skill.name, skill.metadata.name, *skill.metadata.aliases]
            if any(candidate.lower() == wanted for candidate in names):
                return skill
        return None

    def find_by_capability(self, capability: str) -> list[Skill]:
        wanted = capability.strip().lower()
        return [
            skill
            for skill in self.list_skills()
            if any(cap.lower() == wanted for cap in skill.metadata.capabilities)
        ]

    def _match_by_text(self, text: str) -> Skill | None:
        lowered = text.lower()
        scored: list[tuple[int, Skill]] = []
        for skill in self.list_skills():
            score = 0
            for hint in skill.metadata.routing_hints + skill.metadata.aliases + skill.metadata.tags:
                if hint and hint.lower() in lowered:
                    score += 1
            for example in skill.metadata.examples:
                tokens = [t for t in example.lower().split()[:3] if t]
                if any(token in lowered for token in tokens):
                    score += 1
            if score:
                scored.append((score, skill))
        if not scored:
            return None
        scored.sort(key=lambda item: (-item[0], item[1].metadata.priority))
        return scored[0][1]

    def choose(self, ctx: SkillContext) -> Skill:
        explicit = str(ctx.metadata.get("skill") or "").strip()
        if explicit:
            skill = self.get(explicit)
            if skill is not None:
                return skill

        if ctx.task_type == "analyze":
            matches = self.find_by_capability("repo_analysis")
            if matches:
                return matches[0]

        if ctx.task_type in {"edit", "agent"}:
            matches = self.find_by_capability("safe_edit")
            if matches:
                return matches[0]

        if ctx.user_request:
            matched = self._match_by_text(ctx.user_request)
            if matched is not None:
                return matched

        candidates = [skill for skill in self.list_skills() if skill.can_handle(ctx)]
        if candidates:
            return candidates[0]

        raise ValueError("找不到可處理此任務的 skill")


class AnalyzeRepoSkill:
    name = "analyze_repo"
    description = "分析 repo 結構、重點檔案與摘要資訊的唯讀 skill"
    metadata = SkillMetadata(
        name="analyze_repo",
        description="分析 repo 結構、重要入口、模組分佈與聚焦檔案摘要",
        version="2.0",
        capabilities=["repo_analysis", "repo_overview"],
        tags=["analysis", "read-only", "overview"],
        aliases=["analyze", "overview", "scan"],
        examples=["請分析這個專案", "scan this repo", "show project overview"],
        routing_hints=["分析", "overview", "scan", "repo", "structure"],
        requires_session=False,
        requires_validation=False,
        priority=10,
        enabled=True,
    )

    EXCLUDED_DIR_NAMES = {
        ".git", ".hg", ".svn", ".venv", "venv", "__pycache__", ".pytest_cache",
        ".mypy_cache", ".ruff_cache", ".tox", "node_modules", "build", "dist",
        ".idea", ".vscode", ".coverage",
    }
    EXCLUDED_DIR_SUFFIXES = {".egg-info"}
    EXCLUDED_DIR_FRAGMENTS = {
        "agent_runtime/sandbox_workspaces",
        "agent_runtime/snapshots",
        "agent_runtime/sessions",
    }
    EXCLUDED_FILE_SUFFIXES = {".pyc", ".pyo", ".log", ".tmp", ".cache"}
    EXCLUDED_FILE_NAMES = {".coverage"}

    def can_handle(self, ctx: SkillContext) -> bool:
        if ctx.task_type == "analyze":
            return True
        text = (ctx.user_request or "").lower()
        return any(word in text for word in ["analyze", "analysis", "分析", "掃描", "overview", "結構", "repo"])

    def plan(self, ctx: SkillContext) -> SkillPlan:
        return SkillPlan(
            self.name,
            "repo_analysis",
            "分析 codebase 結構並回傳第二輪降噪後的專案摘要。",
            ["掃描專案目錄", "忽略 runtime/packaging 噪音", "整理模組摘要", "產出重點概覽"],
        )

    def _normalize_relpath(self, path: str) -> str:
        return path.replace(os.sep, "/")

    def _should_skip_dir(self, relative_dir: str) -> bool:
        rel = self._normalize_relpath(relative_dir).strip("/")
        if not rel:
            return False
        parts = [p for p in rel.split("/") if p]
        if any(part in self.EXCLUDED_DIR_NAMES for part in parts):
            return True
        if any(part.endswith(suffix) for part in parts for suffix in self.EXCLUDED_DIR_SUFFIXES):
            return True
        return any(fragment in rel for fragment in self.EXCLUDED_DIR_FRAGMENTS)

    def _should_skip_file(self, relpath: str) -> bool:
        rel = self._normalize_relpath(relpath)
        filename = os.path.basename(rel)
        if filename in self.EXCLUDED_FILE_NAMES:
            return True
        if any(filename.endswith(suffix) for suffix in self.EXCLUDED_FILE_SUFFIXES):
            return True
        if any(part.endswith(".egg-info") for part in rel.split("/")):
            return True
        if "agent_runtime/sessions/" in rel:
            return True
        return False

    def _categorize(self, relpath: str) -> str:
        lower = relpath.lower()
        if lower.startswith("tests/") or "/tests/" in lower or lower.startswith("test_"):
            return "tests"
        if lower.startswith("repo_guardian_mcp/services/") or "/services/" in lower:
            return "services"
        if lower.startswith("repo_guardian_mcp/tools/") or "/tools/" in lower:
            return "tools"
        if lower.endswith(".py"):
            return "python"
        if lower.endswith(".md"):
            return "markdown"
        if lower.endswith((".yml", ".yaml", ".toml", ".json", ".ini")):
            return "config"
        return "other"

    def execute(self, ctx: SkillContext, plan: SkillPlan) -> SkillResult:
        files: list[str] = []
        category_counts = {
            "python": 0, "markdown": 0, "config": 0, "tests": 0, "services": 0, "tools": 0, "other": 0,
        }

        for root, dirnames, filenames in os.walk(ctx.repo_root):
            rel_dir = os.path.relpath(root, ctx.repo_root)
            rel_dir = "" if rel_dir == "." else self._normalize_relpath(rel_dir)
            dirnames[:] = [
                name for name in dirnames
                if not self._should_skip_dir("/".join(filter(None, [rel_dir, name])))
            ]
            for name in filenames:
                relpath = os.path.relpath(os.path.join(root, name), ctx.repo_root)
                relpath = self._normalize_relpath(relpath)
                if self._should_skip_file(relpath):
                    continue
                files.append(relpath)
                category_counts[self._categorize(relpath)] += 1

        files.sort()

        try:
            top_level_entries = sorted(
                entry for entry in os.listdir(ctx.repo_root)
                if not self._should_skip_dir(entry) and not entry.endswith(".egg-info")
            )
        except OSError:
            top_level_entries = []

        key_files = [
            item for item in files
            if item in {
                "README.md",
                "pyproject.toml",
                ".env.example",
                "requirements.txt",
                "uv.lock",
                "repo_guardian_mcp/cli.py",
                "repo_guardian_mcp/skills.py",
                "repo_guardian_mcp/tools/run_task_pipeline.py",
            }
        ]

        important_modules = {
            "services": sorted([item for item in files if item.startswith("repo_guardian_mcp/services/")])[:10],
            "tools": sorted([item for item in files if item.startswith("repo_guardian_mcp/tools/")])[:10],
            "tests": sorted([item for item in files if item.startswith("tests/")])[:10],
        }

        summary = {
            "repo_name": os.path.basename(os.path.abspath(ctx.repo_root)),
            "top_level_entries": top_level_entries[:20],
            "key_files": key_files,
            "category_counts": category_counts,
            "important_modules": important_modules,
            "ignored_directories": sorted(self.EXCLUDED_DIR_NAMES),
            "ignored_path_fragments": sorted(self.EXCLUDED_DIR_FRAGMENTS),
            "ignored_dir_suffixes": sorted(self.EXCLUDED_DIR_SUFFIXES),
        }

        result = {
            "ok": True,
            "mode": "analysis",
            "file_count": len(files),
            "displayed_file_count": min(len(files), 120),
            "summary": summary,
            "files": files[:120],
        }
        return SkillResult(ok=True, skill_name=self.name, output=result)

    def validate(self, ctx: SkillContext, result: SkillResult) -> dict[str, Any]:
        has_files = result.ok and bool(result.output.get("files"))
        has_summary = bool(result.output.get("summary"))
        passed = has_files and has_summary
        return {
            "passed": passed,
            "status": "pass" if passed else "fail",
            "checks": [
                {
                    "name": "analysis_has_files",
                    "status": "pass" if has_files else "fail",
                    "message": "analysis produced focused file list" if has_files else "analysis returned no files",
                },
                {
                    "name": "analysis_has_summary",
                    "status": "pass" if has_summary else "fail",
                    "message": "analysis produced repo summary" if has_summary else "analysis summary missing",
                },
            ],
            "summary": "Analysis validated" if passed else "Analysis validation failed",
        }


class SafeEditSkill:
    name = "safe_edit"
    description = "在 sandbox session 中安全修改檔案並驗證的 skill"
    metadata = SkillMetadata(
        name="safe_edit",
        description="在 sandbox session 中安全修改檔案、產生 diff 並執行 validation",
        version="2.0",
        capabilities=["safe_edit", "file_edit", "validation"],
        tags=["editing", "sandbox", "validation"],
        aliases=["edit", "modify", "patch"],
        examples=["append text to README.md", "replace string in file", "修改檔案並驗證"],
        routing_hints=["edit", "modify", "replace", "append", "patch", "修改", "替換"],
        requires_session=True,
        requires_validation=True,
        priority=20,
        enabled=True,
    )

    def __init__(self, orchestrator: EditExecutionOrchestrator | None = None) -> None:
        self._orchestrator = orchestrator or EditExecutionOrchestrator()

    def can_handle(self, ctx: SkillContext) -> bool:
        return ctx.task_type in {"edit", "auto", "agent"}

    def plan(self, ctx: SkillContext) -> SkillPlan:
        target = ctx.relative_path if not ctx.operations else f"{len(ctx.operations)} operations"
        return SkillPlan(
            self.name,
            "safe_edit",
            f"在 sandbox 中修改 {target}，預覽 diff 並執行 validation。",
            ["建立或恢復 session", "套用修改", "預覽 diff", "執行 validation", "持久化 session"],
            True,
            True,
        )

    def execute(self, ctx: SkillContext, plan: SkillPlan) -> SkillResult:
        if ctx.session_id:
            result = self._orchestrator.edit_existing_session(
                repo_root=ctx.repo_root,
                session_id=ctx.session_id,
                relative_path=ctx.relative_path,
                content=ctx.content,
                mode=ctx.mode,
                old_text=ctx.old_text,
                operations=ctx.operations,
            )
        else:
            result = self._orchestrator.run(
                repo_root=ctx.repo_root,
                relative_path=ctx.relative_path,
                content=ctx.content,
                mode=ctx.mode,
                old_text=ctx.old_text,
                operations=ctx.operations,
            )
        return SkillResult(
            ok=bool(result.get("ok")),
            skill_name=self.name,
            output=result,
            error=result.get("error"),
            validation=dict(result.get("validation") or {}),
            session_id=result.get("session_id"),
        )

    def validate(self, ctx: SkillContext, result: SkillResult) -> dict[str, Any]:
        if result.validation:
            return result.validation
        passed = result.ok
        return {
            "passed": passed,
            "status": "pass" if passed else "fail",
            "checks": [
                {
                    "name": "skill_result_ok",
                    "status": "pass" if passed else "fail",
                    "message": "safe edit finished" if passed else (result.error or "safe edit failed"),
                }
            ],
            "summary": "Safe edit validated" if passed else "Safe edit validation failed",
        }
