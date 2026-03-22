from repo_guardian_mcp.services.task_orchestrator import TaskOrchestrator


class FakeFlow:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    def execute_analyze(self, **kwargs):
        self.calls.append(("analyze", kwargs))
        return {"ok": True, "mode": "analysis"}

    def execute_agent(self, **kwargs):
        self.calls.append(("agent", kwargs))
        return {"ok": True, "mode": "run"}

    def execute_edit(self, **kwargs):
        self.calls.append(("edit", kwargs))
        return {"ok": True, "mode": "edit"}


def test_task_orchestrator_only_routes_to_flow():
    flow = FakeFlow()
    orchestrator = TaskOrchestrator(flow=flow)

    a = orchestrator.run(repo_root=".", task_type="analyze", user_request="請分析")
    b = orchestrator.run(repo_root=".", task_type="auto", user_request="請分析")
    c = orchestrator.run(repo_root=".", task_type="edit", relative_path="README.md", content="x")

    assert a["ok"] is True and b["ok"] is True and c["ok"] is True
    assert [name for name, _ in flow.calls] == ["analyze", "agent", "edit"]

