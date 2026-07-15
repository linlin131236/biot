from pathlib import Path
import threading

import pytest
from fastapi.testclient import TestClient

from bolt_core.app import create_app
from bolt_core.model_settings import ModelSettingsConflictError, ModelSettingsStore
from bolt_core.persistence.database import Database
from bolt_core.persistence.repositories import ControlPlaneRepository


class FakeCredentials:
    def __init__(self, values: dict[str, str] | None = None) -> None:
        self.values = dict(values or {})
        self.delete_calls: list[str] = []

    def load(self, credential_id: str) -> str | None:
        return self.values.get(credential_id)

    def delete(self, credential_id: str) -> None:
        self.delete_calls.append(credential_id)
        self.values.pop(credential_id, None)


def _repository(tmp_path) -> ControlPlaneRepository:
    return _repository_from_root(tmp_path / "user-data")


def _repository_from_root(data_root) -> ControlPlaneRepository:
    return ControlPlaneRepository(Database.open(data_root))


def _payload(revision: int, credential_id: str | None = "credential-123") -> dict:
    return {
        "revision": revision,
        "provider": "openai-compatible",
        "base_url": "https://api.example/v1",
        "model": "gpt-test",
        "temperature": 0.7,
        "timeout": 45.0,
        "context_window": 32768,
        "credential_id": credential_id,
    }


def test_persistent_model_settings_reload_all_non_secret_fields_after_store_recreation(tmp_path):
    repository = _repository(tmp_path)
    credentials = FakeCredentials({"credential-123": "api-key-canary-1234567890"})
    first = ModelSettingsStore(repository=repository, credential_store=credentials)

    saved = first.update(_payload(0))
    restarted = ModelSettingsStore(repository=repository, credential_store=credentials)

    assert saved.state == "ready"
    assert restarted.status().revision == 0
    assert restarted.config().provider == "openai-compatible"
    assert restarted.config().base_url == "https://api.example/v1"
    assert restarted.config().model == "gpt-test"
    assert restarted.config().temperature == 0.7
    assert restarted.config().timeout == 45.0
    assert restarted.config().context_window == 32768
    assert restarted.config().credential_id == "credential-123"


def test_persistent_model_settings_rejects_stale_revision_without_overwriting(tmp_path):
    repository = _repository(tmp_path)
    credentials = FakeCredentials({"credential-123": "safe-secret"})
    first = ModelSettingsStore(repository=repository, credential_store=credentials)
    first.update(_payload(0))
    stale = ModelSettingsStore(repository=repository, credential_store=credentials)
    first.update({"revision": 0, "model": "current-model"})

    with pytest.raises(ModelSettingsConflictError):
        stale.update({"revision": 0, "model": "stale-model"})

    assert ModelSettingsStore(repository=repository, credential_store=credentials).config().model == "current-model"


def test_initial_persistent_model_settings_race_returns_stable_conflict(tmp_path):
    database_root = tmp_path / "user-data"
    credentials = FakeCredentials({"credential-123": "safe-secret"})
    first = ModelSettingsStore(repository=_repository_from_root(database_root), credential_store=credentials)
    second = ModelSettingsStore(repository=_repository_from_root(database_root), credential_store=credentials)
    start = threading.Barrier(2)
    outcomes: list[BaseException | str] = []

    def save(store: ModelSettingsStore) -> None:
        start.wait()
        try:
            store.update(_payload(0))
        except BaseException as error:
            outcomes.append(error)
        else:
            outcomes.append("ok")

    threads = [threading.Thread(target=save, args=(store,)) for store in (first, second)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert outcomes.count("ok") == 1
    assert sum(isinstance(result, ModelSettingsConflictError) for result in outcomes) == 1


def test_readback_mismatch_restores_previous_persisted_model(tmp_path):
    repository = _repository(tmp_path)
    credentials = FakeCredentials({"credential-123": "safe-secret"})
    store = ModelSettingsStore(repository=repository, credential_store=credentials)
    store.update(_payload(0))
    original_load = repository.load_model_profile
    reads = 0

    def mismatched_once(profile_id):
        nonlocal reads
        reads += 1
        profile = original_load(profile_id)
        return {**profile, "model": "unexpected-model"} if profile["model"] == "new-model" else profile

    repository.load_model_profile = mismatched_once
    with pytest.raises(RuntimeError, match="model settings readback mismatch"):
        store.update({"revision": 0, "model": "new-model"})

    restarted = ModelSettingsStore(repository=repository, credential_store=credentials)
    assert restarted.config().model == "gpt-test"


def test_readback_recovery_conflict_refreshes_store_and_raises_domain_conflict(tmp_path):
    repository = _repository(tmp_path)
    credentials = FakeCredentials({"credential-123": "safe-secret"})
    store = ModelSettingsStore(repository=repository, credential_store=credentials)
    store.update(_payload(0))
    original_load = repository.load_model_profile
    raced = False

    def raced_mismatch(profile_id):
        nonlocal raced
        profile = original_load(profile_id)
        if profile["model"] == "new-model" and not raced:
            raced = True
            repository.load_model_profile = original_load
            try:
                repository.update_model_profile(profile_id, 1, {"model": "other-model"})
            finally:
                repository.load_model_profile = raced_mismatch
            return {**profile, "model": "unexpected-model"}
        return profile

    repository.load_model_profile = raced_mismatch
    with pytest.raises(ModelSettingsConflictError, match="readback recovery conflict"):
        store.update({"revision": 0, "model": "new-model"})

    assert store.config().model == "other-model"
    assert store.status().revision == 2


@pytest.mark.parametrize(
    "field, value",
    [("apiKey", "secret"), ("Authorization", "Bearer secret"), ("unsupported", True)],
)
def test_model_settings_rejects_sensitive_variants_and_unknown_fields(field, value, tmp_path):
    repository = _repository(tmp_path)
    store = ModelSettingsStore(repository=repository, credential_store=FakeCredentials())

    with pytest.raises(ValueError):
        store.update({"revision": 0, field: value})

    with pytest.raises(KeyError):
        repository.load_model_profile("default")


def test_missing_credential_is_explicitly_blocked_not_configured(tmp_path):
    repository = _repository(tmp_path)
    store = ModelSettingsStore(repository=repository, credential_store=FakeCredentials())

    status = store.update(_payload(0))

    assert status.state == "blocked"
    assert status.blocked_reason == "credential_not_found"
    assert status.has_api_key is False


def test_deleting_model_profile_never_deletes_credential_manager_value(tmp_path):
    repository = _repository(tmp_path)
    credentials = FakeCredentials({"credential-123": "safe-secret"})
    store = ModelSettingsStore(repository=repository, credential_store=credentials)
    store.update(_payload(0))

    store.delete(revision=0)

    assert credentials.delete_calls == []
    assert credentials.load("credential-123") == "safe-secret"
    assert store.status().credential_id is None


def test_failed_persistent_write_keeps_last_verified_config(monkeypatch, tmp_path):
    repository = _repository(tmp_path)
    credentials = FakeCredentials({"credential-123": "safe-secret"})
    store = ModelSettingsStore(repository=repository, credential_store=credentials)
    store.update(_payload(0))

    def fail_update(*_args, **_kwargs):
        raise OSError("simulated write failure")

    monkeypatch.setattr(repository, "update_model_profile", fail_update)
    with pytest.raises(OSError, match="simulated write failure"):
        store.update({"revision": 0, "model": "must-not-replace"})

    assert store.config().model == "gpt-test"


def test_save_rejects_repository_readback_that_differs_from_requested_config(monkeypatch, tmp_path):
    repository = _repository(tmp_path)
    credentials = FakeCredentials({"credential-123": "safe-secret"})
    store = ModelSettingsStore(repository=repository, credential_store=credentials)
    original_load = repository.load_model_profile

    def mismatched_load(profile_id):
        profile = original_load(profile_id)
        return {**profile, "model": "unexpected-model"}

    monkeypatch.setattr(repository, "load_model_profile", mismatched_load)
    with pytest.raises(RuntimeError, match="model settings readback mismatch"):
        store.update(_payload(0))

    assert store.config().model == "gpt-4o"


def test_model_settings_rejects_runtime_capability_overrides(tmp_path):
    repository = _repository(tmp_path)
    store = ModelSettingsStore(repository=repository, credential_store=FakeCredentials())

    with pytest.raises(ValueError, match="unsupported model settings field"):
        store.update({"revision": 0, "capability_overrides": {"tool_calling": False}})

    with pytest.raises(KeyError):
        repository.load_model_profile("default")


def test_app_and_harness_real_restart_restore_settings_without_secret_on_disk(tmp_path):
    user_data = tmp_path / "electron-user-data"
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    canary = "api-key-canary-1234567890"
    credentials = FakeCredentials({"credential-123": canary})
    first_app = create_app(
        project_dir=workspace,
        persistence_root=user_data,
        credential_store=credentials,
    )
    with TestClient(first_app) as first_client:
        response = first_client.post("/model/settings", json=_payload(0))
        assert response.status_code == 200
        assert canary not in str(response.json())

    second_app = create_app(
        project_dir=workspace,
        persistence_root=user_data,
        credential_store=credentials,
    )
    with TestClient(second_app) as second_client:
        restored = second_client.get("/model/settings")
        assert restored.status_code == 200
        assert restored.json()["model"] == "gpt-test"
        assert restored.json()["context_window"] == 32768
        assert "capability_overrides" not in restored.json()
        assert canary not in str(restored.json())

    assert first_app.state.harness is not second_app.state.harness
    second_app.state.persistence.database.create_backup("task3-secret-canary")
    for path in user_data.rglob("*"):
        if path.is_file():
            assert canary.encode("utf-8") not in path.read_bytes(), Path(path)


def test_model_settings_delete_endpoint_removes_only_profile_reference(tmp_path):
    user_data = tmp_path / "electron-user-data"
    credentials = FakeCredentials({"credential-123": "safe-secret"})
    app = create_app(
        project_dir=tmp_path,
        persistence_root=user_data,
        credential_store=credentials,
    )
    with TestClient(app) as client:
        assert client.post("/model/settings", json=_payload(0)).status_code == 200
        deleted = client.delete("/model/settings", params={"revision": 0})
        status = client.get("/model/settings")

    assert deleted.status_code == 200
    assert deleted.json()["state"] == "unconfigured"
    assert status.json()["credential_id"] is None
    assert credentials.delete_calls == []
    assert credentials.load("credential-123") == "safe-secret"


def test_model_settings_rejects_api_key_payload_without_persisting_it(tmp_path):
    repository = _repository(tmp_path)
    store = ModelSettingsStore(repository=repository, credential_store=FakeCredentials())
    payload = _payload(0)
    payload["api_key"] = "synthetic-secret-canary-1234567890"

    with pytest.raises(ValueError, match="sensitive model settings fields"):
        store.update(payload)

    with pytest.raises(KeyError):
        repository.load_model_profile("default")


def test_missing_credential_blocks_agent_execution_before_gateway_call(tmp_path):
    from bolt_core.harness import Harness

    harness = Harness(
        workspace=str(tmp_path),
        persistence=_repository(tmp_path),
        credential_store=FakeCredentials(),
    )
    harness.update_model_settings(_payload(0))
    run = harness.create_run("must not run without configured credential")

    result = harness.run_agent_step(run.id)

    assert result.status == "failed"
    assert result.error == "credential_not_found"
    assert not any(event.type == "llm.requested" for event in harness.trace(run.id))


def test_unavailable_credential_manager_blocks_agent_execution_before_gateway_call(tmp_path):
    from bolt_core.harness import Harness

    class UnavailableCredentials:
        def load(self, _credential_id: str) -> str | None:
            raise OSError("credential manager unavailable")

    repository = _repository(tmp_path)
    ModelSettingsStore(
        repository=repository,
        credential_store=FakeCredentials({"credential-123": "safe-secret"}),
    ).update(_payload(0))
    harness = Harness(
        workspace=str(tmp_path),
        persistence=repository,
        credential_store=UnavailableCredentials(),
    )
    run = harness.create_run("must not run while credential manager is unavailable")

    result = harness.run_agent_step(run.id)

    assert harness.model_settings.status().state == "blocked"
    assert harness.model_settings.status().blocked_reason == "credential_not_found"
    assert result.status == "failed"
    assert result.error == "credential_not_found"
    assert not any(event.type == "llm.requested" for event in harness.trace(run.id))
