from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any


class RoutingObservabilityService:
    """Build routing/chaining/fallback observability reports."""

    def summarize_results(self, results: list[dict[str, Any]]) -> dict[str, Any]:
        selected_skill_counts: Counter[str] = Counter()
        fallback_counts: Counter[str] = Counter()
        chain_edges: Counter[str] = Counter()
        errors: Counter[str] = Counter()

        for item in results:
            skill = str(item.get("selected_skill") or "unknown")
            selected_skill_counts[skill] += 1

            for fallback in item.get("fallback_skills") or []:
                fallback_counts[str(fallback)] += 1

            for chain in item.get("chain_to") or []:
                chain_edges[f"{skill}->{chain}"] += 1

            error_code = str(item.get("error_code") or "")
            if error_code:
                errors[error_code] += 1

        return {
            "selected_skill_counts": dict(selected_skill_counts),
            "fallback_counts": dict(fallback_counts),
            "chain_edges": dict(chain_edges),
            "error_code_counts": dict(errors),
            "total_results": len(results),
        }

    def summarize_agent_sessions(self, repo_root: str) -> dict[str, Any]:
        sessions_dir = Path(repo_root).resolve() / "agent_runtime" / "agent_sessions"
        if not sessions_dir.exists():
            return {"total_sessions": 0, "selected_skill_counts": {}, "last_error_counts": {}}

        skill_counts: Counter[str] = Counter()
        error_counts: Counter[str] = Counter()

        for path in sessions_dir.glob("*.json"):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            skill = str(payload.get("selected_skill") or "unknown")
            skill_counts[skill] += 1
            err = ((payload.get("last_execution") or {}).get("error") or {}).get("code")
            if err:
                error_counts[str(err)] += 1

        return {
            "total_sessions": sum(skill_counts.values()),
            "selected_skill_counts": dict(skill_counts),
            "last_error_counts": dict(error_counts),
        }

