from bolt_core.harness import Harness
from bolt_core.app import create_app
from bolt_core.model_gateway import ModelResponse, TokenUsage
from bolt_core.workspace_credential_gate import LockedWorkspace
from fastapi.testclient import TestClient


class CapturingGateway:
    def __init__(self):
        self.requests = []

    def complete(self, request):
        self.requests.append(request)
        return ModelResponse("completed", "done", TokenUsage(1, 1, 2), [], None)


def test_harness_attaches_server_owned_workspace_binding_to_model_request(tmp_path):
    gateway = CapturingGateway()
    binding = LockedWorkspace("workspace-anonymous-id", 6)
    harness = Harness(
        workspace=str(tmp_path),
        locked_workspace=str(tmp_path),
        locked_workspace_binding=binding,
        model_gateway=gateway,
    )
    run = harness.create_run("answer with text")

    result = harness.run_agent_step(run.id)

    assert result.status == "completed"
    assert gateway.requests[0].locked_workspace == binding


def test_app_composition_injects_gateway_and_server_workspace_binding(tmp_path):
    gateway = CapturingGateway()
    binding = LockedWorkspace("workspace-anonymous-id", 6)
    app = create_app(
        execution_audit_path=tmp_path / "audit.json",
        project_dir=tmp_path,
        lock_default_workspace=True,
        model_gateway=gateway,
        locked_workspace_binding=binding,
    )
    client = TestClient(app)
    run_id = client.post("/harness/runs", json={"goal": "answer with text"}).json()["id"]

    response = client.post(f"/harness/runs/{run_id}/agent-steps")

    assert response.json()["status"] == "completed"
    assert gateway.requests[0].locked_workspace == binding
