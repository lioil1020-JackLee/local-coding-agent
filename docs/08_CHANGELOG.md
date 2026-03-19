# CHANGELOG

## 2026-03-19

### 目前穩定基準
- `uv run pytest`
- **40 passed**

---

## 2026-03-19（chat mode 初版 + skill registry v2 基礎結構）

### chat mode 初版
新增：
- `repo-guardian chat <repo_root>`
- `repo-guardian chat <repo_root> --message "<text>" --once`

支援：
- `/help`
- `/skills`
- `/plan <text>`
- `/run <text>`
- `/exit`

目前 chat mode 先以 CLI REPL 骨架為主，目的是讓 repo-guardian 從「命令集合」往「可持續互動的 agent 介面」前進。

### skill registry v2 基礎結構
skill metadata 新增：
- `aliases`
- `examples`
- `routing_hints`
- `enabled`

registry 新增：
- `find_by_capability()`
- alias lookup
- hint-based routing
- capability-based routing
- priority-based ordering

### 文件同步更新
同步更新：
- `README.md`
- `docs/08_CHANGELOG.md`
- `docs/09_變更與進度.md`\n