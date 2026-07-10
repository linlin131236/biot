from fastapi.testclient import TestClient

from bolt_core.app import create_app
from bolt_core.credential_lifecycle import CredentialLifecycle, InMemoryCredentialConfigStore
from bolt_core.windows_credential_manager import new_credential_id


class FakeCredentials:
    def __init__(self):
        self.values: dict[str, str] = {}

    def save(self, credential_id: str, secret: str) -> None:
        self.values[credential_id] = secret

    def load(self, credential_id: str) -> str | None:
        return self.values.get(credential_id)

    def delete(self, credential_id: str) -> None:
        self.values.pop(credential_id, None)


def test_production_settings_api_adds_and_deletes_through_credential_lifecycle(tmp_path):
    credentials = FakeCredentials()
    configs = InMemoryCredentialConfigStore()
    lifecycle = CredentialLifecycle(credentials, configs, id_factory=new_credential_id)
    app = create_app(
        execution_audit_path=tmp_path / "audit.json",
        project_dir=tmp_path,
        credential_lifecycle=lifecycle,
        credential_configs=configs,
    )
    client = TestClient(app)

    added = client.post("/desktop/settings/api-key", json={"api_key": "synthetic-secret", "revision": 0})

    assert added.status_code == 200
    assert added.json() == {"status": "ok", "has_api_key": True, "revision": 2}
    assert list(credentials.values.values()) == ["synthetic-secret"]
    status = client.get("/desktop/settings")
    assert status.json()["has_api_key"] is True
    assert status.json()["credential_revision"] == 2
    deleted = client.delete("/desktop/settings/api-key", params={"revision": 2})
    assert deleted.status_code == 200
    assert deleted.json() == {"status": "ok", "has_api_key": False, "revision": 4}
    assert client.get("/desktop/settings").json()["has_api_key"] is False
    assert credentials.values == {}


def test_settings_api_replaces_an_active_key_and_deletes_the_old_credential(tmp_path):
    credentials = FakeCredentials()
    configs = InMemoryCredentialConfigStore()
    lifecycle = CredentialLifecycle(credentials, configs, id_factory=new_credential_id)
    client = TestClient(create_app(
        execution_audit_path=tmp_path / "audit.json",
        project_dir=tmp_path,
        credential_lifecycle=lifecycle,
        credential_configs=configs,
    ))
    first = client.post(
        "/desktop/settings/api-key",
        json={"api_key": "first-secret", "revision": 0},
    ).json()
    old_id = next(iter(credentials.values))

    replaced = client.post(
        "/desktop/settings/api-key",
        json={"api_key": "second-secret", "revision": first["revision"]},
    )

    assert replaced.status_code == 200
    assert replaced.json() == {"status": "ok", "has_api_key": True, "revision": 4}
    assert old_id not in credentials.values
    assert list(credentials.values.values()) == ["second-secret"]
    assert client.get("/desktop/settings").json()["credential_revision"] == 4
