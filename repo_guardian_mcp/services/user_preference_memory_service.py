from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


class UserPreferenceMemoryService:
    """儲存並更新使用者偏好，讓代理可以跨回合維持一致風格。"""

    def _memory_file(self, repo_root: str) -> Path:
        path = Path(repo_root).resolve() / "agent_runtime" / "user_memory"
        path.mkdir(parents=True, exist_ok=True)
        return path / "preferences.json"

    def load(self, *, repo_root: str) -> dict[str, Any]:
        path = self._memory_file(repo_root)
        if not path.exists():
            return self._default_profile()
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return self._default_profile()
        profile = self._default_profile()
        if isinstance(payload, dict):
            profile.update({k: payload[k] for k in payload.keys() if k in profile})
            if isinstance(payload.get("signals"), dict):
                profile["signals"].update(payload["signals"])
        return profile

    def save(self, *, repo_root: str, profile: dict[str, Any]) -> None:
        path = self._memory_file(repo_root)
        profile = dict(profile)
        profile["updated_at_ms"] = int(time.time() * 1000)
        path.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")

    def update_from_user_request(self, *, repo_root: str, user_request: str) -> dict[str, Any]:
        text = (user_request or "").strip().lower()
        profile = self.load(repo_root=repo_root)

        signals: dict[str, Any] = dict(profile.get("signals") or {})

        def hit(name: str) -> None:
            signals[name] = int(signals.get(name) or 0) + 1

        if any(token in text for token in ("白話", "好懂", "新手", "生活化")):
            profile["prefer_plain_language"] = True
            hit("plain_language")
        if any(token in text for token in ("不要術語", "少術語", "不要專有名詞", "別太工程")):
            profile["avoid_jargon"] = True
            hit("avoid_jargon")
        if any(token in text for token in ("簡短", "重點就好", "一句話", "短一點")):
            profile["response_length"] = "short"
            hit("short_response")
        if any(token in text for token in ("詳細", "完整", "越詳細越好", "多一點")):
            profile["response_length"] = "long"
            hit("long_response")
        if any(token in text for token in ("一步一步", "慢慢來", "分步", "步驟")):
            profile["step_by_step"] = True
            hit("step_by_step")
        if any(token in text for token in ("不用我一直問", "你自己做完", "自己接著做", "不用我催")):
            profile["prefer_autonomous_execution"] = True
            hit("autonomous")

        profile["signals"] = signals
        self.save(repo_root=repo_root, profile=profile)
        return profile

    def build_style_hint(self, *, profile: dict[str, Any]) -> str:
        hints: list[str] = []
        if profile.get("prefer_plain_language"):
            hints.append("請用白話、短句，像對一般使用者說明。")
        if profile.get("avoid_jargon"):
            hints.append("避免工程術語，必要時才補一個簡短名詞。")
        if profile.get("step_by_step"):
            hints.append("請分步驟回答，每步 1-2 句。")
        length = str(profile.get("response_length") or "medium")
        if length == "short":
            hints.append("回答以重點為主，盡量精簡。")
        elif length == "long":
            hints.append("回答可完整一些，但仍保持好懂。")
        if profile.get("prefer_autonomous_execution"):
            hints.append("若任務可自動接續，請直接執行到一個可交付結果再回報。")
        return " ".join(hints).strip()

    def _default_profile(self) -> dict[str, Any]:
        return {
            "prefer_plain_language": True,
            "avoid_jargon": True,
            "response_length": "medium",
            "step_by_step": True,
            "prefer_autonomous_execution": True,
            "signals": {},
            "updated_at_ms": 0,
        }
