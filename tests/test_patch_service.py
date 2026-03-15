import json
from pathlib import Path

from repo_guardian_mcp.tools.preview_diff import preview_diff
from repo_guardian_mcp.tools.propose_patch import propose_patch
from repo_guardian_mcp.tools.stage_patch import stage_patch


TARGET_FILE = "repo_guardian_mcp/tools/propose_patch.py"


def main():
    target_path = Path(TARGET_FILE)
    original_text = target_path.read_text(encoding="utf-8")

    resp = propose_patch(
        task="Add a module-level comment line above the propose_patch function in repo_guardian_mcp/tools/propose_patch.py",
        relevant_paths=[
            TARGET_FILE,
        ],
        context_snippets=[
            "def propose_patch(",
        ],
        constraints=[
            "Modify only repo_guardian_mcp/tools/propose_patch.py",
            "Use the existing text anchor 'def propose_patch(' only",
            "Do not reference any return statement as an anchor",
            "Keep changes minimal",
            "Do not introduce new dependencies",
            "Insert exactly one single-line Python comment",
        ],
        max_files_to_change=1,
        require_tests=False,
        allow_new_files=False,
        repo_root=".",
    )

    print("RESULT:")
    print(json.dumps(resp, ensure_ascii=False, indent=2))

    if not resp["ok"]:
        print("\nSTOP: propose_patch failed")
        return

    preview = preview_diff(
        patch=resp["result"],
        repo_root=".",
    )

    print("\nPREVIEW:\n")
    print(json.dumps(preview, ensure_ascii=False, indent=2))

    if not preview["ok"]:
        print("\nSTOP: preview_diff failed")
        return

    stage = stage_patch(
        patch=resp["result"],
        repo_root=".",
    )

    print("\nSTAGE RESULT:\n")
    print(json.dumps(stage, ensure_ascii=False, indent=2))

    if not stage["ok"]:
        print("\nSTOP: stage_patch failed")
        return

    updated_text = target_path.read_text(encoding="utf-8")

    print("\nFILE CHANGED:\n")
    print(updated_text != original_text)

    print("\nUPDATED FILE PREVIEW:\n")
    print(updated_text[:800])

    # Optional: restore original file so repeated test runs stay clean.
    target_path.write_text(original_text, encoding="utf-8")
    print("\nRESTORED ORIGINAL FILE:\nTrue")


if __name__ == "__main__":
    main()