from __future__ import annotations

"""
資料模型定義。

目前依賴 pydantic 以簡化驗證與序列化。
"""

from datetime import datetime
from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, model_validator


# ============================================================
# Common / Shared Models
# ============================================================


class ToolResult(BaseModel):
    ok: bool = True
    message: str | None = None


class TaskSession(BaseModel):
    session_id: str = Field(..., description="Unique task session id")
    repo_root: str = Field(..., description="Absolute path to the main repository root")
    sandbox_path: str = Field(..., description="Absolute path to this session's sandbox worktree")
    branch_name: str = Field(..., description="Git branch name created for this sandbox session")
    base_branch: str = Field(..., description="Original branch name at session creation time")
    base_commit: str = Field(..., description="Git commit SHA used as the sandbox base")
    created_at: datetime = Field(..., description="Session creation time in UTC")
    status: str = Field(default="active", description="Session status, e.g. active/closed/rolled_back")
    last_validation_status: Optional[str] = Field(
        default=None,
        description="Optional latest validation status, e.g. passed/failed",
    )


# ============================================================
# Repo Overview Models
# ============================================================


class RepoOverviewResult(BaseModel):
    repo_root: str
    repo_name: str
    total_files: int
    languages: list[str] = Field(default_factory=list)
    top_level_dirs: list[str] = Field(default_factory=list)
    entrypoint_candidates: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


# ============================================================
# Patch Proposal Models
# ============================================================


class PatchOperationType(str, Enum):
    CREATE_FILE = "create_file"
    DELETE_FILE = "delete_file"
    REPLACE_RANGE = "replace_range"
    INSERT_AT = "insert_at"


class PatchAnchorMode(str, Enum):
    LINE = "line"
    TEXT = "text"


class FileChangeSafety(str, Enum):
    SAFE = "safe"
    REVIEW_REQUIRED = "review_required"
    HIGH_RISK = "high_risk"


class PatchTarget(BaseModel):
    path: str = Field(..., description="Repository-relative file path")
    must_exist: bool = Field(
        default=True,
        description="Whether the file must already exist before applying the operation",
    )


class ReplaceRangeAnchor(BaseModel):
    mode: PatchAnchorMode = Field(..., description="How the target range is anchored")

    start_line: int | None = Field(
        default=None,
        ge=1,
        description="1-based inclusive start line when mode='line'",
    )
    end_line: int | None = Field(
        default=None,
        ge=1,
        description="1-based inclusive end line when mode='line'",
    )

    start_text: str | None = Field(
        default=None,
        description="Start anchor text when mode='text'",
    )
    end_text: str | None = Field(
        default=None,
        description="End anchor text when mode='text'",
    )

    @model_validator(mode="after")
    def validate_anchor(self) -> "ReplaceRangeAnchor":
        if self.mode == PatchAnchorMode.LINE:
            if self.start_line is None or self.end_line is None:
                raise ValueError("start_line and end_line are required when mode='line'")
            if self.end_line < self.start_line:
                raise ValueError("end_line must be >= start_line")

        if self.mode == PatchAnchorMode.TEXT:
            if not self.start_text or not self.end_text:
                raise ValueError("start_text and end_text are required when mode='text'")

        return self


class InsertAtAnchor(BaseModel):
    mode: PatchAnchorMode = Field(..., description="How the insertion point is anchored")

    line: int | None = Field(
        default=None,
        ge=1,
        description="1-based insertion line when mode='line'",
    )
    text: str | None = Field(
        default=None,
        description="Anchor text when mode='text'",
    )

    position: Literal["before", "after"] = Field(
        default="after",
        description="Insert before or after the anchor",
    )

    @model_validator(mode="after")
    def validate_anchor(self) -> "InsertAtAnchor":
        if self.mode == PatchAnchorMode.LINE and self.line is None:
            raise ValueError("line is required when mode='line'")

        if self.mode == PatchAnchorMode.TEXT and not self.text:
            raise ValueError("text is required when mode='text'")

        return self


class PatchOperation(BaseModel):
    op_id: str = Field(..., description="Stable operation id for tracing/debugging")
    type: PatchOperationType
    target: PatchTarget

    reason: str = Field(..., description="Why this operation is needed")

    content: str | None = Field(
        default=None,
        description="New content for create_file / replace_range / insert_at",
    )
    range: ReplaceRangeAnchor | None = Field(
        default=None,
        description="Required when type='replace_range'",
    )
    insert_at: InsertAtAnchor | None = Field(
        default=None,
        description="Required when type='insert_at'",
    )

    @model_validator(mode="after")
    def validate_by_type(self) -> "PatchOperation":
        if self.type == PatchOperationType.CREATE_FILE:
            if not self.content:
                raise ValueError("content is required for create_file")
            if self.target.must_exist:
                raise ValueError("target.must_exist must be False for create_file")

        elif self.type == PatchOperationType.DELETE_FILE:
            if self.content is not None:
                raise ValueError("content must be None for delete_file")
            if self.range is not None:
                raise ValueError("range must be None for delete_file")
            if self.insert_at is not None:
                raise ValueError("insert_at must be None for delete_file")

        elif self.type == PatchOperationType.REPLACE_RANGE:
            if not self.content:
                raise ValueError("content is required for replace_range")
            if self.range is None:
                raise ValueError("range is required for replace_range")
            if self.insert_at is not None:
                raise ValueError("insert_at must be None for replace_range")

        elif self.type == PatchOperationType.INSERT_AT:
            if not self.content:
                raise ValueError("content is required for insert_at")
            if self.insert_at is None:
                raise ValueError("insert_at is required for insert_at")
            if self.range is not None:
                raise ValueError("range must be None for insert_at")

        return self


class FileChangeSummary(BaseModel):
    path: str
    change_type: Literal["create", "modify", "delete"]
    safety: FileChangeSafety = Field(default=FileChangeSafety.REVIEW_REQUIRED)
    summary: str


class ProposePatchRequest(BaseModel):
    task: str = Field(..., description="What the agent is asked to implement or change")

    repo_root: str | None = Field(
        default=None,
        description="Optional absolute repo root, if available at runtime",
    )

    relevant_paths: list[str] = Field(
        default_factory=list,
        description="Files likely relevant to this change",
    )
    readonly_paths: list[str] = Field(
        default_factory=list,
        description="Files/directories that must not be modified",
    )

    context_snippets: list[str] = Field(
        default_factory=list,
        description="Important code/context snippets prepared by upstream tools",
    )
    impact_summary: str | None = Field(
        default=None,
        description="Result summary from impact analysis, if available",
    )

    constraints: list[str] = Field(
        default_factory=list,
        description="Implementation constraints, coding style, runtime/platform limits",
    )

    max_files_to_change: int = Field(
        default=5,
        ge=1,
        le=50,
        description="Hard ceiling for number of files modified in this proposal",
    )
    require_tests: bool = Field(
        default=True,
        description="Whether the proposal should include tests when appropriate",
    )
    allow_new_files: bool = Field(
        default=True,
        description="Whether the proposal may create new files",
    )


class ProposePatchResponse(BaseModel):
    success: bool = True

    summary: str = Field(..., description="High-level summary of proposed change")
    rationale: str = Field(..., description="Why this patch shape was chosen")

    operations: list[PatchOperation] = Field(default_factory=list)
    files: list[FileChangeSummary] = Field(default_factory=list)

    risks: list[str] = Field(default_factory=list)
    followups: list[str] = Field(default_factory=list)
    test_plan: list[str] = Field(default_factory=list)

    raw_model_output: dict[str, Any] | None = Field(
        default=None,
        description="Optional raw structured model output for debugging",
    )

    @model_validator(mode="after")
    def validate_consistency(self) -> "ProposePatchResponse":
        touched_paths = {op.target.path for op in self.operations}
        declared_paths = {f.path for f in self.files}

        if declared_paths and touched_paths != declared_paths:
            missing_in_files = touched_paths - declared_paths
            missing_in_ops = declared_paths - touched_paths

            details: list[str] = []
            if missing_in_files:
                details.append(f"missing file summaries for: {sorted(missing_in_files)}")
            if missing_in_ops:
                details.append(f"file summaries without operations: {sorted(missing_in_ops)}")

            raise ValueError("; ".join(details))

        return self