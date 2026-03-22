from repo_guardian_mcp.services.sandbox_service import create_copy_sandbox


def test_create_copy_sandbox_ignores_temp_like_dirs(tmp_path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / "README.md").write_text("hello\n", encoding="utf-8")

    tmp_dir = repo_root / ".tmp"
    tmp_dir.mkdir()
    (tmp_dir / "secret.txt").write_text("do not copy\n", encoding="utf-8")

    odd_tmp = repo_root / "..tmppytest"
    odd_tmp.mkdir()
    (odd_tmp / "x.txt").write_text("do not copy\n", encoding="utf-8")

    sandbox = create_copy_sandbox(repo_root=repo_root, session_id="abc123")
    assert (sandbox / "README.md").exists()
    assert not (sandbox / ".tmp").exists()
    assert not (sandbox / "..tmppytest").exists()
