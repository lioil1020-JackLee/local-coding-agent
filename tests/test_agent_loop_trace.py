from repo_guardian_mcp.agent_loop import AgentLoop


def test_trace_analyze():
    loop = AgentLoop()
    result = loop.run("幫我分析 repo")
    assert result["ok"] is True
    assert result["mode"] == "analyze"
    assert result["trace"][0]["step"] == "analyze"


def test_trace_edit():
    loop = AgentLoop()
    result = loop.run("幫我修改 README")
    assert result["mode"] == "edit"
    assert len(result["trace"]) == 2
    assert [step["step"] for step in result["trace"]] == ["analyze", "edit"]


def test_trace_chat():
    loop = AgentLoop()
    result = loop.run("這是什麼")
    assert result["mode"] == "chat"
    assert result["trace"][0]["step"] == "chat"


def test_retry_success_after_fail():
    calls = {"n": 0}

    def flaky():
        calls["n"] += 1
        if calls["n"] == 1:
            raise ValueError("fail once")
        return "ok"

    loop = AgentLoop(max_retries=1)
    trace = []
    result = loop._trace_step(trace, "test", flaky)
    assert result["ok"] is True
    assert trace[0]["ok"] is False
    assert trace[1]["ok"] is True


def test_retry_fail():
    def always_fail():
        raise ValueError("fail")

    loop = AgentLoop(max_retries=1)
    trace = []
    result = loop._trace_step(trace, "test", always_fail)
    assert result["ok"] is False
    assert len(trace) == 2


def test_run_edit_failure_propagation():
    loop = AgentLoop(max_retries=0)

    def fake_trace(trace, name, func):
        if name == "edit":
            trace.append({"step": "edit", "ok": False, "attempt": 1, "error": "boom"})
            return {"ok": False, "error": "boom"}
        trace.append({"step": name, "ok": True, "attempt": 1})
        return {"ok": True}

    loop._trace_step = fake_trace

    result = loop.run("幫我修改 README")
    assert result["ok"] is False
    assert result["mode"] == "edit"
    assert result["fallback_mode"] == "plan"


def test_edit_fallback_to_plan():
    loop = AgentLoop(max_retries=0)

    def fail_edit(trace, name, func):
        if name == "edit":
            trace.append({"step": "edit", "ok": False, "attempt": 1, "error": "boom"})
            return {"ok": False, "error": "boom"}
        trace.append({"step": name, "ok": True, "attempt": 1})
        return {"ok": True}

    loop._trace_step = fail_edit
    result = loop.run("幫我修改 README")
    assert result["ok"] is False
    assert result["fallback_mode"] == "plan"


def test_analyze_fallback_to_chat():
    loop = AgentLoop(max_retries=0)

    def fail_analyze(trace, name, func):
        if name == "analyze":
            trace.append({"step": "analyze", "ok": False, "attempt": 1, "error": "boom"})
            return {"ok": False, "error": "boom"}
        trace.append({"step": name, "ok": True, "attempt": 1})
        return {"ok": True}

    loop._trace_step = fail_analyze
    result = loop.run("幫我分析 repo")
    assert result["ok"] is False
    assert result["fallback_mode"] == "chat"
