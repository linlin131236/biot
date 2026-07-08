"""API tests for approval-gated patch apply."""
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from bolt_core.approval_apply_api import create_approval_apply_router
from bolt_core.write_tool_proposal import OP_MODIFY, RISK_LOW, STATUS_APPROVED, WriteProposalStore


def _approved_store(tmp_path: Path) -> tuple[WriteProposalStore, str]:
    store = WriteProposalStore(project_dir=str(tmp_path))
    verification = store.create(
        tool_id="write_file",
        target_files=["src/main.py"],
        operation_type=OP_MODIFY,
        before_summary="old",
        after_summary="new",
        diff_preview=(
            "--- a/src/main.py\n"
            "+++ b/src/main.py\n"
            "@@ -1 +1 @@\n"
            "-print('old')\n"
            "+print('new')\n"
        ),
        risk_level=RISK_LOW,
        required_permissions=["write"],
        rollback_hint="git checkout src/main.py",
        chinese_explanation="修改 main.py",
    )
    proposal = verification.proposal
    store._proposals[proposal.proposal_id] = proposal.__class__(
        proposal_id=proposal.proposal_id,
        tool_id=proposal.tool_id,
        target_files=proposal.target_files,
        operation_type=proposal.operation_type,
        before_summary=proposal.before_summary,
        after_summary=proposal.after_summary,
        diff_preview=proposal.diff_preview,
        risk_level=proposal.risk_level,
        required_permissions=proposal.required_permissions,
        rollback_hint=proposal.rollback_hint,
        chinese_explanation=proposal.chinese_explanation,
        git_head=proposal.git_head,
        status=STATUS_APPROVED,
        created_at=proposal.created_at,
    )
    return store, proposal.proposal_id


def _client(store: WriteProposalStore, tmp_path: Path) -> TestClient:
    app = FastAPI()
    app.include_router(create_approval_apply_router(store=store, project_dir=str(tmp_path)))
    return TestClient(app)


def test_apply_api_injects_human_actor_and_ignores_request_actor(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("print('old')\n", encoding="utf-8")
    store, proposal_id = _approved_store(tmp_path)
    client = _client(store, tmp_path)

    response = client.post(
        "/tools/approval/apply",
        json={"proposal_id": proposal_id, "approval": {"actor": "agent", "scope": "wrong"}},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["result"]["audit_record"]["actor"] == "human"
    assert (tmp_path / "src" / "main.py").read_text(encoding="utf-8") == "print('new')\n"


def test_apply_api_preserves_forged_rejection(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("print('old')\n", encoding="utf-8")
    store, proposal_id = _approved_store(tmp_path)
    client = _client(store, tmp_path)

    response = client.post(
        "/tools/approval/apply",
        json={"proposal_id": proposal_id, "approval": {"forged": True}},
    )

    assert response.status_code == 400
    assert "伪造" in response.json()["detail"]
    assert (tmp_path / "src" / "main.py").read_text(encoding="utf-8") == "print('old')\n"
