from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any
from urllib import error, request

from repo_guardian_mcp.models import (
    PatchOperationType,
    ProposePatchRequest,
    ProposePatchResponse,
)


class PatchServiceError(Exception):
    """Base exception for patch service errors."""


class PatchModelError(PatchServiceError):
    """Raised when the model response cannot be parsed or validated."""


class PatchPolicyError(PatchServiceError):
    """Raised when the generated patch violates local policy."""


class PatchService:
    def __init__(
        self,
        base_url: str | None = None,
        model_name: str | None = None,
        temperature: float = 0.2,
        timeout_seconds: int = 120,
    ) -> None:
        self.base_url = (base_url or os.getenv("LM_STUDIO_BASE_URL", "http://127.0.0.1:1234/v1")).rstrip("/")
        self.model_name = model_name or os.getenv("LM_STUDIO_MODEL", "local-model")
        self.temperature = temperature
        self.timeout_seconds = timeout_seconds

        self._service_dir = Path(__file__).resolve().parent
        self._package_dir = self._service_dir.parent
        self._project_root = self._package_dir.parent
        self._prompt_path = self._package_dir / "prompts" / "patch_generation.txt"

    def propose_patch(self, req: ProposePatchRequest) -> ProposePatchResponse:
        system_prompt = self._load_system_prompt()
        user_prompt = self._build_user_prompt(req)

        raw_response = self._call_lm_studio(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )

        parsed_json = self._extract_json_payload(raw_response)
        response = self._parse_response(parsed_json)

        response.raw_model_output = parsed_json
        self._enforce_policy(req, response)

        return response

    def _load_system_prompt(self) -> str:
        if self._prompt_path.exists():
            return self._prompt_path.read_text(encoding="utf-8").strip()

        return (
            "You are a repository patch planning assistant.\n"
            "Generate a structured patch proposal as JSON only.\n"
            "Do not output markdown.\n"
            "Do not include explanations outside JSON.\n"
            "Respect readonly paths and file-count limits.\n"
            "Prefer minimal, safe, localized changes.\n"
        )

    def _build_user_prompt(self, req: ProposePatchRequest) -> str:
        payload = {
            "task": req.task,
            "repo_root": req.repo_root,
            "relevant_paths": req.relevant_paths,
            "readonly_paths": req.readonly_paths,
            "context_snippets": req.context_snippets,
            "impact_summary": req.impact_summary,
            "constraints": req.constraints,
            "max_files_to_change": req.max_files_to_change,
            "require_tests": req.require_tests,
            "allow_new_files": req.allow_new_files,
            "output_contract": {
                "must_return_json": True,
                "top_level_keys": [
                    "success",
                    "summary",
                    "rationale",
                    "operations",
                    "files",
                    "risks",
                    "followups",
                    "test_plan",
                ],
                "operation_types": [
                    "create_file",
                    "delete_file",
                    "replace_range",
                    "insert_at",
                ],
                "notes": [
                    "operations must be minimal and repository-relative",
                    "files must match touched paths in operations",
                    "for create_file, target.must_exist must be false",
                    "for replace_range, include range",
                    "for insert_at, include insert_at",
                    "do not modify readonly_paths",
                    "do not exceed max_files_to_change",
                ],
            },
        }

        return json.dumps(payload, ensure_ascii=False, indent=2)

    def _call_lm_studio(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        url = f"{self.base_url}/chat/completions"

        body = {
            "model": self.model_name,
            "temperature": self.temperature,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "text"},
        }

        data = json.dumps(body).encode("utf-8")
        req = request.Request(
            url=url,
            data=data,
            headers={
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with request.urlopen(req, timeout=self.timeout_seconds) as resp:
                raw = resp.read().decode("utf-8")
                return json.loads(raw)
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise PatchServiceError(
                f"LM Studio HTTP error: {exc.code} {exc.reason} | {detail}"
            ) from exc
        except error.URLError as exc:
            raise PatchServiceError(
                f"Cannot connect to LM Studio at {url}: {exc.reason}"
            ) from exc
        except TimeoutError as exc:
            raise PatchServiceError("LM Studio request timed out") from exc
        except json.JSONDecodeError as exc:
            raise PatchServiceError("LM Studio returned non-JSON response") from exc

    def _extract_json_payload(self, raw_response: dict[str, Any]) -> dict[str, Any]:
        try:
            content = raw_response["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise PatchModelError("Malformed chat completion response") from exc

        if isinstance(content, list):
            content = "".join(
                part.get("text", "") for part in content if isinstance(part, dict)
            )

        if not isinstance(content, str) or not content.strip():
            raise PatchModelError("Model returned empty content")

        content = content.strip()

        try:
            parsed = json.loads(content)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

        fenced_match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", content, re.DOTALL)
        if fenced_match:
            try:
                parsed = json.loads(fenced_match.group(1))
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                pass

        brace_match = re.search(r"(\{.*\})", content, re.DOTALL)
        if brace_match:
            try:
                parsed = json.loads(brace_match.group(1))
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                pass

        raise PatchModelError("Could not extract valid JSON object from model output")

    def _parse_response(self, payload: dict[str, Any]) -> ProposePatchResponse:
        try:
            return ProposePatchResponse.model_validate(payload)
        except Exception as exc:
            raise PatchModelError(f"Model output failed schema validation: {exc}") from exc

    def _enforce_policy(
        self,
        req: ProposePatchRequest,
        resp: ProposePatchResponse,
    ) -> None:
        touched_paths = [op.target.path for op in resp.operations]
        unique_paths = sorted(set(touched_paths))
        readonly_prefixes = tuple(req.readonly_paths)

        if len(unique_paths) > req.max_files_to_change:
            raise PatchPolicyError(
                f"Patch touches {len(unique_paths)} files, exceeds max_files_to_change={req.max_files_to_change}"
            )

        repo_root_path = Path(req.repo_root).resolve() if req.repo_root else None

        for op in resp.operations:
            target_path = op.target.path.strip()

            if not target_path:
                raise PatchPolicyError("Operation has empty target path")

            if target_path.startswith("/") or target_path.startswith("\\"):
                raise PatchPolicyError(f"Absolute paths are not allowed: {target_path}")

            if ".." in Path(target_path).parts:
                raise PatchPolicyError(f"Parent path traversal is not allowed: {target_path}")

            if readonly_prefixes and self._is_under_readonly(target_path, readonly_prefixes):
                raise PatchPolicyError(f"Attempted to modify readonly path: {target_path}")

            if op.type == PatchOperationType.CREATE_FILE and not req.allow_new_files:
                raise PatchPolicyError(f"Creating new files is not allowed: {target_path}")

            if op.type == PatchOperationType.DELETE_FILE:
                raise PatchPolicyError(
                    f"delete_file is disabled in v1 for safety: {target_path}"
                )

            if repo_root_path is not None:
                self._validate_workspace_anchor(repo_root_path, op)

    @staticmethod
    def _is_under_readonly(path: str, readonly_prefixes: tuple[str, ...]) -> bool:
        normalized = path.strip("/\\")
        for prefix in readonly_prefixes:
            clean_prefix = prefix.strip("/\\")
            if normalized == clean_prefix or normalized.startswith(clean_prefix + "/"):
                return True
        return False
    
    def _validate_workspace_anchor(self, repo_root: Path, op) -> None:
        file_path = repo_root / op.target.path

        if op.type == PatchOperationType.CREATE_FILE:
            return

        if not file_path.exists():
            raise PatchPolicyError(f"Target file does not exist in workspace: {op.target.path}")

        try:
            text = file_path.read_text(encoding="utf-8")
        except Exception as exc:
            raise PatchPolicyError(
                f"Cannot read target file for anchor validation: {op.target.path} | {exc}"
            ) from exc

        if op.type == PatchOperationType.INSERT_AT and op.insert_at is not None:
            if op.insert_at.mode.value == "text":
                anchor = op.insert_at.text
                if not anchor:
                    raise PatchPolicyError(f"Missing insert_at text anchor: {op.target.path}")
                if anchor not in text:
                    raise PatchPolicyError(
                        f"insert_at text anchor not found in workspace file {op.target.path}: {anchor!r}"
                    )

        if op.type == PatchOperationType.REPLACE_RANGE and op.range is not None:
            if op.range.mode.value == "text":
                start_text = op.range.start_text
                end_text = op.range.end_text

                if not start_text or not end_text:
                    raise PatchPolicyError(
                        f"replace_range text anchors incomplete: {op.target.path}"
                    )

                if start_text not in text:
                    raise PatchPolicyError(
                        f"replace_range start_text not found in workspace file {op.target.path}: {start_text!r}"
                    )

                if end_text not in text:
                    raise PatchPolicyError(
                        f"replace_range end_text not found in workspace file {op.target.path}: {end_text!r}"
                    )