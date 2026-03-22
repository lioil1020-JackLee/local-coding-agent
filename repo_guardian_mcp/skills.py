from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
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
    chain_to: list[str] = field(default_factory=list)
    fallback_skills: list[str] = field(default_factory=list)


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
    can_chain_to: list[str] = field(default_factory=list)
    fallback_skills: list[str] = field(default_factory=list)
    manifest_path: str | None = None


@dataclass
class SkillManifest:
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
    can_chain_to: list[str] = field(default_factory=list)
    fallback_skills: list[str] = field(default_factory=list)
    implementation: str | None = None
    manifest_path: str | None = None

    @classmethod
    def from_dict(cls, raw: dict[str, Any], manifest_path: str | None = None) -> "SkillManifest":
        data = dict(raw)
        missing = [key for key in ("name", "description") if not str(data.get(key) or "").strip()]
        if missing:
            raise ValueError(f"skill manifest 缺少必要欄位: {', '.join(missing)}")

        for key in (
            "capabilities",
            "tags",
            "aliases",
            "examples",
            "routing_hints",
            "can_chain_to",
            "fallback_skills",
        ):
            value = data.get(key)
            if value is None:
                data[key] = []
            elif isinstance(value, str):
                data[key] = [value]
            else:
                data[key] = [str(item) for item in value]

        data["enabled"] = bool(data.get("enabled", True))
        data["priority"] = int(data.get("priority", 100))
        data.setdefault("manifest_path", manifest_path)
        return cls(**data)

    @classmethod
    def from_json_file(cls, path: str | os.PathLike[str]) -> "SkillManifest":
        manifest_path = Path(path).resolve()
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("skill manifest 必須是 JSON object")
        return cls.from_dict(payload, manifest_path=str(manifest_path))

    def to_metadata(self) -> SkillMetadata:
        return SkillMetadata(
            name=self.name,
            description=self.description,
            version=self.version,
            capabilities=list(self.capabilities),
            tags=list(self.tags),
            aliases=list(self.aliases),
            examples=list(self.examples),
            routing_hints=list(self.routing_hints),
            requires_session=self.requires_session,
            requires_validation=self.requires_validation,
            priority=self.priority,
            enabled=self.enabled,
            can_chain_to=list(self.can_chain_to),
            fallback_skills=list(self.fallback_skills),
            manifest_path=self.manifest_path,
        )


class GenericManifestSkill:
    def __init__(self, manifest: SkillManifest) -> None:
        self.name = manifest.name
        self.description = manifest.description
        self.metadata = manifest.to_metadata()
        self.manifest = manifest

    def can_handle(self, ctx: SkillContext) -> bool:
        if not self.metadata.enabled:
            return False
        text = (ctx.user_request or "").lower()
        for token in [*self.metadata.routing_hints, *self.metadata.aliases, *self.metadata.tags]:
            if token and token.lower() in text:
                return True
        if ctx.task_type != "auto":
            return any(cap.lower() == ctx.task_type.lower() for cap in self.metadata.capabilities)
        return False

    def plan(self, ctx: SkillContext) -> SkillPlan:
        return SkillPlan(
            skill_name=self.name,
            intent=self.metadata.capabilities[0] if self.metadata.capabilities else "generic",
            summary=self.description,
            steps=["讀取 manifest skill metadata", "回報目前尚未綁定可執行實作"],
            requires_validation=self.metadata.requires_validation,
            requires_session=self.metadata.requires_session,
            chain_to=list(self.metadata.can_chain_to),
            fallback_skills=list(self.metadata.fallback_skills),
        )

    def execute(self, ctx: SkillContext, plan: SkillPlan) -> SkillResult:
        return SkillResult(
            ok=False,
            skill_name=self.name,
            output={"ok": False, "manifest": asdict(self.manifest)},
            error=f"skill '{self.name}' 目前只有 manifest，尚未提供可執行 implementation",
        )

    def validate(self, ctx: SkillContext, result: SkillResult) -> dict[str, Any]:
        passed = bool(result.ok)
        return {
            "passed": passed,
            "status": "pass" if passed else "fail",
            "checks": [
                {
                    "name": "manifest_skill_bound",
                    "status": "pass" if passed else "fail",
                    "message": "manifest skill executed" if passed else (result.error or "manifest skill is not executable"),
                }
            ],
            "summary": "Manifest skill validated" if passed else "Manifest skill validation failed",
        }


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
        self._manifests: dict[str, SkillManifest] = {}
        for skill in skills or []:
            self.register(skill)

    def register(self, skill: Skill) -> None:
        existing = self.get_any(getattr(skill, "name", ""))
        if existing is not None:
            self._skills = [item for item in self._skills if item is not existing]
        self._skills.append(skill)
        self._skills.sort(key=lambda item: getattr(item.metadata, "priority", 100))

    def register_manifest(self, manifest: SkillManifest, skill: Skill | None = None) -> Skill:
        self._manifests[manifest.name] = manifest
        registered = skill or GenericManifestSkill(manifest)
        metadata = registered.metadata
        metadata.can_chain_to = list(manifest.can_chain_to)
        metadata.fallback_skills = list(manifest.fallback_skills)
        metadata.enabled = manifest.enabled
        metadata.manifest_path = manifest.manifest_path
        self.register(registered)
        return registered

    def register_manifest_file(self, path: str | os.PathLike[str], skill: Skill | None = None) -> Skill:
        manifest = SkillManifest.from_json_file(path)
        return self.register_manifest(manifest, skill=skill)

    def set_enabled(self, name: str, enabled: bool) -> bool:
        skill = self.get_any(name)
        if skill is None:
            return False
        skill.metadata.enabled = enabled
        return True

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
                    "can_chain_to": list(skill.metadata.can_chain_to),
                    "fallback_skills": list(skill.metadata.fallback_skills),
                    "manifest_path": skill.metadata.manifest_path,
                }
            )
        return data

    def get_any(self, name: str) -> Skill | None:
        wanted = name.strip().lower()
        if not wanted:
            return None
        for skill in self._skills:
            names = [skill.name, skill.metadata.name, *skill.metadata.aliases]
            if any(candidate.lower() == wanted for candidate in names if candidate):
                return skill
        return None

    def get(self, name: str) -> Skill | None:
        skill = self.get_any(name)
        if skill is None or not skill.metadata.enabled:
            return None
        return skill

    def get_manifest(self, name: str) -> SkillManifest | None:
        return self._manifests.get(name)

    def find_by_capability(self, capability: str) -> list[Skill]:
        wanted = capability.strip().lower()
        return [
            skill
            for skill in self.list_skills()
            if any(cap.lower() == wanted for cap in skill.metadata.capabilities)
        ]

    def next_skills(self, name: str) -> list[Skill]:
        skill = self.get(name)
        if skill is None:
            return []
        resolved: list[Skill] = []
        for next_name in skill.metadata.can_chain_to:
            candidate = self.get(next_name)
            if candidate is not None:
                resolved.append(candidate)
        return resolved

    def fallback_skills_for(self, name: str) -> list[Skill]:
        skill = self.get(name)
        if skill is None:
            return []
        resolved: list[Skill] = []
        for fallback_name in skill.metadata.fallback_skills:
            candidate = self.get(fallback_name)
            if candidate is not None:
                resolved.append(candidate)
        return resolved

    def _match_by_text(self, text: str) -> Skill | None:
        lowered = text.lower()
        scored: list[tuple[int, Skill]] = []
        for skill in self.list_skills():
            score = 0
            for hint in skill.metadata.routing_hints + skill.metadata.aliases + skill.metadata.tags:
                if hint and hint.lower() in lowered:
                    score += 1
            for example in skill.metadata.examples:
                tokens = [t for t in example.lower().split()[:3] if t and len(t) >= 4]
                if any(token in lowered for token in tokens):
                    score += 1
            if score:
                scored.append((score, skill))
        if not scored:
            return None
        scored.sort(key=lambda item: (-item[0], item[1].metadata.priority))
        return scored[0][1]

    def choose(self, ctx: SkillContext) -> Skill:
        route_policy = str((ctx.metadata or {}).get("routing_policy") or "auto")
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

        if route_policy in {"auto", "text_first"} and ctx.user_request:
            matched = self._match_by_text(ctx.user_request)
            if matched is not None:
                return matched

        candidates = [skill for skill in self.list_skills() if skill.can_handle(ctx)]
        if candidates:
            return candidates[0]

        raise ValueError("找不到可用的 skill")


class AnalyzeRepoSkill:
    def __init__(self) -> None:
        self.metadata = SkillMetadata(**asdict(type(self).metadata))

    name = "analyze_repo"
    description = "分析 repo 結構與重點，提供新手可讀的白話摘要 skill"
    metadata = SkillMetadata(
        name="analyze_repo",
        description="分析 repo 結構、重要檔案與入口點，並輸出白話重點摘要",
        version="3.0",
        capabilities=["repo_analysis", "repo_overview"],
        tags=["analysis", "read-only", "overview"],
        aliases=["analyze", "overview", "scan", "分析", "看懂", "概覽"],
        examples=["請分析這個專案", "scan this repo", "show project overview"],
        routing_hints=["分析", "看懂", "概覽", "狀態", "入口", "架構", "專案", "overview", "scan", "repo", "structure"],
        requires_session=False,
        requires_validation=False,
        priority=10,
        enabled=True,
        can_chain_to=["safe_edit"],
        fallback_skills=[],
    )

    EXCLUDED_DIR_NAMES = {
        ".git", ".hg", ".svn", ".venv", "venv", "__pycache__", ".pytest_cache",
        ".mypy_cache", ".ruff_cache", ".tox", "node_modules", "build", "dist",
        ".idea", ".vscode", ".coverage", "agent_runtime", ".uv-cache", ".tmp",
        ".tmp-pytest", ".tmp-pytest-run", "..tmppytest", "pytest-of-lioil", "tmp_pytest_local",
    }
    EXCLUDED_DIR_PREFIXES = (".tmp-", ".tmp-pytest-run-", "pytest-of-", "tmp_pytest")
    EXCLUDED_DIR_SUFFIXES = {".egg-info"}
    EXCLUDED_DIR_FRAGMENTS = {
        "agent_runtime/sandbox_workspaces",
        "agent_runtime/snapshots",
        "agent_runtime/sessions",
    }
    EXCLUDED_FILE_SUFFIXES = {".pyc", ".pyo", ".log", ".tmp", ".cache"}
    EXCLUDED_FILE_NAMES = {".coverage", "sync.ffs_lock"}

    def can_handle(self, ctx: SkillContext) -> bool:
        if ctx.task_type == "analyze":
            return True
        text = (ctx.user_request or "").lower()
        return any(
            word in text
            for word in [
                "analyze",
                "analysis",
                "overview",
                "scan",
                "repo",
                "status",
                "entrypoint",
                "structure",
                "分析",
                "看懂",
                "概覽",
                "狀態",
                "入口",
                "架構",
                "專案",
            ]
        )

    def plan(self, ctx: SkillContext) -> SkillPlan:
        return SkillPlan(
            self.name,
            "repo_analysis",
            "分析 codebase 結構，整理重點模組與下一步建議。",
            ["掃描專案目錄", "過濾 runtime/暫存資料", "整理重點檔案", "輸出白話摘要"],
            chain_to=list(self.metadata.can_chain_to),
            fallback_skills=list(self.metadata.fallback_skills),
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
        if any(part.startswith(prefix) for part in parts for prefix in self.EXCLUDED_DIR_PREFIXES):
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

    def _describe_runtime_area(self, files: list[str]) -> str:
        if any(item.startswith("repo_guardian_mcp/services/") for item in files):
            return "repo_guardian_mcp/services 是主要執行邏輯區（流程與協調層）。"
        return "目前沒有偵測到明確的 services 執行主線。"

    def _describe_tools_area(self, files: list[str]) -> str:
        if any(item.startswith("repo_guardian_mcp/tools/") for item in files):
            return "repo_guardian_mcp/tools 提供對外工具入口（MCP tool 面向）。"
        return "目前沒有偵測到明確的 tools 入口層。"

    def _describe_tests_area(self, files: list[str]) -> str:
        test_files = [item for item in files if item.startswith("tests/")][:6]
        if not test_files:
            return "tests/ 目前覆蓋較少，建議補上核心流程測試。"
        focus = ", ".join(test_files[:3])
        return f"tests/ 已有測試，代表檔案包含：{focus}"

    def _build_narrative_summary(self, *, top_level_entries: list[str], files: list[str], category_counts: dict[str, int], key_files: list[str], important_modules: dict[str, list[str]]) -> str:
        blocks: list[str] = []
        top_text = ", ".join(top_level_entries[:6]) if top_level_entries else "尚未偵測到明確頂層結構"
        blocks.append(f"這個 repo 的頂層重點包含：{top_text}。")
        blocks.append(self._describe_runtime_area(files))
        blocks.append(self._describe_tools_area(files))
        blocks.append(self._describe_tests_area(files))
        blocks.append(
            f"檔案分布：python={category_counts['python']}、services={category_counts['services']}、tools={category_counts['tools']}、tests={category_counts['tests']}。"
        )
        next_reads = key_files[:3] + important_modules.get("services", [])[:2] + important_modules.get("tools", [])[:2]
        deduped: list[str] = []
        for item in next_reads:
            if item and item not in deduped:
                deduped.append(item)
        if deduped:
            blocks.append(f"建議優先閱讀：{', '.join(deduped[:6])}。")
        return "\n".join(blocks)

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
        narrative_summary = self._build_narrative_summary(
            top_level_entries=top_level_entries,
            files=files,
            category_counts=category_counts,
            key_files=key_files,
            important_modules=important_modules,
        )

        summary = {
            "repo_name": os.path.basename(os.path.abspath(ctx.repo_root)),
            "top_level_entries": top_level_entries[:20],
            "key_files": key_files,
            "category_counts": category_counts,
            "important_modules": important_modules,
            "narrative_summary": narrative_summary,
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
            "narrative_summary": narrative_summary,
            "files": files[:120],
        }
        return SkillResult(ok=True, skill_name=self.name, output=result)

    def validate(self, ctx: SkillContext, result: SkillResult) -> dict[str, Any]:
        has_files = result.ok and bool(result.output.get("files"))
        has_summary = bool(result.output.get("summary"))
        has_narrative = bool((result.output.get("summary") or {}).get("narrative_summary") or result.output.get("narrative_summary"))
        passed = has_files and has_summary and has_narrative
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
                {
                    "name": "analysis_has_narrative",
                    "status": "pass" if has_narrative else "fail",
                    "message": "analysis produced narrative summary" if has_narrative else "analysis narrative summary missing",
                },
            ],
            "summary": "Analysis validated" if passed else "Analysis validation failed",
        }


class SafeEditSkill:
    def __init__(self, orchestrator: EditExecutionOrchestrator | None = None) -> None:
        self.metadata = SkillMetadata(**asdict(type(self).metadata))
        self._orchestrator = orchestrator or EditExecutionOrchestrator()

    name = "safe_edit"
    description = "在 sandbox session 安全修改並自動驗證的 skill"
    metadata = SkillMetadata(
        name="safe_edit",
        description="建立 sandbox session、套用修改、輸出 diff 並執行 validation",
        version="3.0",
        capabilities=["safe_edit", "file_edit", "validation"],
        tags=["editing", "sandbox", "validation"],
        aliases=["edit", "modify", "patch", "修改", "編輯"],
        examples=["append text to README.md", "replace string in file", "幫我修改 README.md"],
        routing_hints=["edit", "modify", "replace", "append", "patch", "修改", "編輯", "套用"],
        requires_session=True,
        requires_validation=True,
        priority=20,
        enabled=True,
        can_chain_to=["analyze_repo"],
        fallback_skills=["analyze_repo"],
    )

    def can_handle(self, ctx: SkillContext) -> bool:
        if ctx.task_type == "edit":
            return True
        if ctx.task_type not in {"auto", "agent"}:
            return False
        text = (ctx.user_request or "").lower()
        edit_tokens = (
            "edit",
            "modify",
            "replace",
            "append",
            "patch",
            "change",
            "修改",
            "編輯",
            "套用",
            "改成",
            "寫入",
        )
        return any(token in text for token in edit_tokens)

    def plan(self, ctx: SkillContext) -> SkillPlan:
        target = ctx.relative_path if not ctx.operations else f"{len(ctx.operations)} operations"
        return SkillPlan(
            self.name,
            "safe_edit",
            f"在 sandbox 安全修改 {target}，並提供 diff 與 validation 結果。",
            ["建立或續接 session", "套用修改", "預覽 diff", "執行 validation", "輸出結果"],
            True,
            True,
            chain_to=list(self.metadata.can_chain_to),
            fallback_skills=list(self.metadata.fallback_skills),
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
