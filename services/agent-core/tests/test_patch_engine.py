from bolt_core.patch_engine import ChangeSet, apply_change_set, build_change_set, can_apply_change


def test_build_change_set_contains_diff_and_base_hash():
    change = build_change_set(
        path="src/app.ts",
        original="const name = 'old';\n",
        proposed="const name = 'Bolt';\n",
    )

    assert isinstance(change, ChangeSet)
    assert change.base_hash
    assert "-const name = 'old';" in change.diff
    assert "+const name = 'Bolt';" in change.diff
    assert change.status == "pending_review"


def test_change_set_rejects_hash_mismatch():
    change = build_change_set(
        path="src/app.ts",
        original="old\n",
        proposed="new\n",
    )

    decision = can_apply_change(change, current_content="user edit\n")

    assert decision.allowed is False
    assert decision.reason == "file changed since proposal"


def test_change_set_allows_matching_hash():
    change = build_change_set(
        path="src/app.ts",
        original="old\n",
        proposed="new\n",
    )

    decision = can_apply_change(change, current_content="old\n")

    assert decision.allowed is True
    assert decision.reason == "base hash matches"


def test_apply_change_set_writes_when_base_hash_matches(tmp_path):
    target = tmp_path / "app.ts"
    target.write_text("old\n", encoding="utf-8")
    change = build_change_set(str(target), "old\n", "new\n")

    decision = apply_change_set(change, str(tmp_path))

    assert decision.allowed is True
    assert decision.reason == "change applied"
    assert target.read_text(encoding="utf-8") == "new\n"


def test_apply_change_set_rejects_when_file_changed(tmp_path):
    target = tmp_path / "app.ts"
    target.write_text("old\n", encoding="utf-8")
    change = build_change_set(str(target), "old\n", "new\n")
    target.write_text("user edit\n", encoding="utf-8")

    decision = apply_change_set(change, str(tmp_path))

    assert decision.allowed is False
    assert decision.reason == "file changed since proposal"
    assert target.read_text(encoding="utf-8") == "user edit\n"


def test_apply_change_set_denies_outside_workspace(tmp_path):
    workspace = tmp_path / "workspace"
    outside = tmp_path / "outside.ts"
    workspace.mkdir()
    outside.write_text("old\n", encoding="utf-8")
    change = build_change_set(str(outside), "old\n", "new\n")

    decision = apply_change_set(change, str(workspace))

    assert decision.allowed is False
    assert decision.reason == "path outside workspace"
    assert outside.read_text(encoding="utf-8") == "old\n"


def test_apply_change_set_denies_secret_path(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    secret = workspace / ".env"
    secret.write_text("TOKEN=old\n", encoding="utf-8")
    change = build_change_set(str(secret), "TOKEN=old\n", "TOKEN=new\n")

    decision = apply_change_set(change, str(workspace))

    assert decision.allowed is False
    assert decision.reason == "secret path denied"
    assert secret.read_text(encoding="utf-8") == "TOKEN=old\n"
