from dataclasses import replace

import pytest

from bolt_core.credential_lifecycle import (
    CredentialConfig,
    CredentialLifecycle,
    CredentialLifecycleError,
    InMemoryCredentialConfigStore,
    JsonCredentialConfigStore,
)
from bolt_core.windows_credential_manager import new_credential_id


class FakeCredentials:
    def __init__(self):
        self.values: dict[str, str] = {}
        self.deleted: list[str] = []
        self.fail_reads = False
        self.fail_delete = False

    def save(self, credential_id: str, secret: str) -> None:
        self.values[credential_id] = secret

    def load(self, credential_id: str) -> str | None:
        if self.fail_reads:
            raise RuntimeError("read failed")
        return self.values.get(credential_id)

    def delete(self, credential_id: str) -> None:
        if self.fail_delete:
            raise RuntimeError("delete failed")
        self.deleted.append(credential_id)
        self.values.pop(credential_id, None)


def test_delete_disables_active_config_before_native_delete_then_commits_absent():
    credentials = FakeCredentials()
    credential_id = new_credential_id()
    credentials.values[credential_id] = "secret"
    configs = InMemoryCredentialConfigStore({
        "openai-compatible": CredentialConfig(
            revision=3,
            credential_state="active",
            active_credential_id=credential_id,
        ),
    })
    lifecycle = CredentialLifecycle(credentials, configs, id_factory=new_credential_id)

    result = lifecycle.delete("openai-compatible", expected_revision=3)

    assert configs.history[0].credential_state == "credential_deleting"
    assert configs.history[0].active_credential_id is None
    assert configs.history[0].pending_credential_id == credential_id
    assert credentials.load(credential_id) is None
    assert result.credential_state == "absent"
    assert result.active_credential_id is None


def test_delete_failure_remains_deleting_and_never_reactivates_key():
    credentials = FakeCredentials()
    credential_id = new_credential_id()
    credentials.values[credential_id] = "secret"
    credentials.fail_delete = True
    configs = InMemoryCredentialConfigStore({
        "openai-compatible": CredentialConfig(
            revision=1,
            credential_state="active",
            active_credential_id=credential_id,
        ),
    })
    lifecycle = CredentialLifecycle(credentials, configs, id_factory=new_credential_id)

    with pytest.raises(CredentialLifecycleError, match="credential_delete_failed"):
        lifecycle.delete("openai-compatible", expected_revision=1)

    state = configs.load("openai-compatible")
    assert state.credential_state == "credential_deleting"
    assert state.active_credential_id is None
    assert state.pending_credential_id == credential_id
    assert credentials.load(credential_id) == "secret"


def test_replace_uses_distinct_target_switches_then_deletes_old():
    credentials = FakeCredentials()
    old_id = new_credential_id()
    credentials.values[old_id] = "old-secret"
    configs = InMemoryCredentialConfigStore({
        "openai-compatible": CredentialConfig(
            revision=4,
            credential_state="active",
            active_credential_id=old_id,
        ),
    })
    lifecycle = CredentialLifecycle(credentials, configs, id_factory=new_credential_id)

    result = lifecycle.replace("openai-compatible", "new-secret", expected_revision=4)

    assert result.credential_state == "active"
    assert result.active_credential_id != old_id
    assert credentials.load(result.active_credential_id) == "new-secret"
    assert old_id in credentials.deleted
    assert configs.history[0].credential_state == "credential_switch_pending"
    assert configs.history[0].active_credential_id == old_id


def test_replace_old_cleanup_failure_keeps_new_id_but_blocks_calls():
    credentials = FakeCredentials()
    old_id = new_credential_id()
    credentials.values[old_id] = "old-secret"
    credentials.fail_delete = True
    configs = InMemoryCredentialConfigStore({
        "openai-compatible": CredentialConfig(
            revision=2,
            credential_state="active",
            active_credential_id=old_id,
        ),
    })
    lifecycle = CredentialLifecycle(credentials, configs, id_factory=new_credential_id)

    with pytest.raises(CredentialLifecycleError, match="credential_cleanup_required"):
        lifecycle.replace("openai-compatible", "new-secret", expected_revision=2)

    state = configs.load("openai-compatible")
    assert state.credential_state == "credential_cleanup_required"
    assert state.active_credential_id is not None
    assert state.active_credential_id != old_id
    assert state.pending_credential_id == old_id


def test_add_commits_active_only_after_write_readback_reload_and_second_readback():
    credentials = FakeCredentials()
    configs = InMemoryCredentialConfigStore()
    lifecycle = CredentialLifecycle(credentials, configs, id_factory=new_credential_id)

    result = lifecycle.add("openai-compatible", "synthetic-secret", expected_revision=0)

    assert result.credential_state == "active"
    assert result.active_credential_id is not None
    assert result.revision == 2
    assert configs.load("openai-compatible") == result
    assert credentials.load(result.active_credential_id) == "synthetic-secret"
    assert configs.history[0].credential_state == "credential_write_pending"
    assert configs.history[0].active_credential_id is None
    assert configs.history[1].credential_state == "active"


def test_add_readback_failure_deletes_attempt_owned_target_and_restores_absent():
    credentials = FakeCredentials()
    credentials.fail_reads = True
    configs = InMemoryCredentialConfigStore()
    lifecycle = CredentialLifecycle(credentials, configs, id_factory=new_credential_id)

    with pytest.raises(CredentialLifecycleError, match="credential_read_failed"):
        lifecycle.add("openai-compatible", "synthetic-secret", expected_revision=0)

    assert configs.load("openai-compatible").credential_state == "absent"
    assert len(credentials.deleted) == 1


def test_add_compensation_delete_failure_enters_recovery_and_blocks_active_id():
    credentials = FakeCredentials()
    credentials.fail_reads = True
    credentials.fail_delete = True
    configs = InMemoryCredentialConfigStore()
    lifecycle = CredentialLifecycle(credentials, configs, id_factory=new_credential_id)

    with pytest.raises(CredentialLifecycleError, match="credential_recovery_required"):
        lifecycle.add("openai-compatible", "synthetic-secret", expected_revision=0)

    recovered = configs.load("openai-compatible")
    assert recovered.credential_state == "credential_recovery_required"
    assert recovered.active_credential_id is None
    assert recovered.pending_credential_id is not None


def test_stale_revision_never_writes_a_credential():
    credentials = FakeCredentials()
    configs = InMemoryCredentialConfigStore({
        "openai-compatible": CredentialConfig(revision=4),
    })
    lifecycle = CredentialLifecycle(credentials, configs, id_factory=new_credential_id)

    with pytest.raises(CredentialLifecycleError, match="credential_revision_changed"):
        lifecycle.add("openai-compatible", "synthetic-secret", expected_revision=3)

    assert credentials.values == {}


def test_json_config_store_persists_compare_and_swap_state_across_restart(tmp_path):
    path = tmp_path / "credential-state.json"
    first = JsonCredentialConfigStore(path)
    saved = first.save(
        "openai-compatible",
        CredentialConfig(credential_state="active", active_credential_id="credential-a"),
        0,
    )

    restarted = JsonCredentialConfigStore(path)

    assert restarted.load("openai-compatible") == saved
    with pytest.raises(CredentialLifecycleError, match="credential_revision_changed"):
        restarted.save("openai-compatible", CredentialConfig(), 0)
