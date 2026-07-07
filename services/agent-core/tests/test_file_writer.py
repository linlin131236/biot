import json

from bolt_core.file_writer import apply_file_write, change_set_json, propose_file_write


def test_propose_file_write_builds_pending_change_set(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    target = workspace / "app.ts"
    target.write_text("old\n", encoding="utf-8")

    proposal = propose_file_write(str(target), "new\n", str(workspace))

    assert proposal.status == "pending_review"
    assert proposal.change is not None
    assert proposal.change.proposed == "new\n"
    assert "-old" in proposal.change.diff
    assert "+new" in proposal.change.diff


def test_propose_file_write_denies_outside_workspace(tmp_path):
    workspace = tmp_path / "workspace"
    outside = tmp_path / "outside.ts"
    workspace.mkdir()
    outside.write_text("old\n", encoding="utf-8")

    proposal = propose_file_write(str(outside), "new\n", str(workspace))

    assert proposal.status == "failed"
    assert proposal.error == "path outside workspace"


def test_apply_file_write_applies_change_set(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    target = workspace / "app.ts"
    target.write_text("old\n", encoding="utf-8")
    proposal = propose_file_write(str(target), "new\n", str(workspace))
    payload = json.loads(change_set_json(proposal.change))

    allowed, reason = apply_file_write(payload, str(workspace))

    assert allowed is True
    assert reason == "change applied"
    assert target.read_text(encoding="utf-8") == "new\n"


def test_apply_file_write_rejects_hash_mismatch(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    target = workspace / "app.ts"
    target.write_text("old\n", encoding="utf-8")
    proposal = propose_file_write(str(target), "new\n", str(workspace))
    target.write_text("user edit\n", encoding="utf-8")

    allowed, reason = apply_file_write(proposal.change.__dict__, str(workspace))

    assert allowed is False
    assert reason == "file changed since proposal"
    assert target.read_text(encoding="utf-8") == "user edit\n"
