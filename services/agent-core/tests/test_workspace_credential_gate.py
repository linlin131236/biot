import pytest
import bolt_core.workspace_credential_gate as gate_module

from bolt_core.workspace_credential_gate import (
    CredentialGateError,
    InMemoryWorkspaceCredentialState,
    LockedWorkspace,
    MigrationState,
    ProviderState,
    WorkspaceCredentialGate,
)


class FakeCredentials:
    def __init__(self):
        self.loads: list[str] = []

    def load(self, credential_id: str) -> str | None:
        self.loads.append(credential_id)
        return "synthetic-secret"


def test_workspace_a_active_while_b_additional_legacy_is_blocked():
    states = InMemoryWorkspaceCredentialState()
    states.set_migration("workspace-a", revision=3, status="committed")
    states.set_migration("workspace-b", revision=8, status="additional_legacy_key")
    states.set_provider("openai", revision=5, state="active", credential_id="credential-a")
    credentials = FakeCredentials()
    gate = WorkspaceCredentialGate(states, credentials)

    lease = gate.resolve(LockedWorkspace("workspace-a", 3), "openai")

    assert lease.secret == "synthetic-secret"
    with pytest.raises(CredentialGateError, match="credential_migration_additional_legacy_key"):
        gate.resolve(LockedWorkspace("workspace-b", 8), "openai")
    assert credentials.loads == ["credential-a"]


def test_restart_reloads_persisted_b_block_without_affecting_a():
    states = InMemoryWorkspaceCredentialState()
    states.set_migration("workspace-a", revision=3, status="committed")
    states.set_migration("workspace-b", revision=8, status="additional_legacy_key")
    states.set_provider("openai", revision=5, state="active", credential_id="credential-a")

    restarted = WorkspaceCredentialGate(states, FakeCredentials())

    assert restarted.resolve(LockedWorkspace("workspace-a", 3), "openai").secret == "synthetic-secret"
    with pytest.raises(CredentialGateError, match="credential_migration_additional_legacy_key"):
        restarted.resolve(LockedWorkspace("workspace-b", 8), "openai")


@pytest.mark.parametrize("status", ["pending", "failed", "conflict", "recovery_required", "committed_cleanup_required"])
def test_all_non_committed_migration_states_block_before_credential_read(status):
    states = InMemoryWorkspaceCredentialState()
    states.set_migration("workspace-b", revision=1, status=status)
    states.set_provider("openai", revision=1, state="active", credential_id="credential-a")
    credentials = FakeCredentials()

    with pytest.raises(CredentialGateError):
        WorkspaceCredentialGate(states, credentials).resolve(LockedWorkspace("workspace-b", 1), "openai")

    assert credentials.loads == []


def test_workspace_revision_is_distinct_from_migration_journal_revision():
    states = InMemoryWorkspaceCredentialState()
    states.set_migration(
        "workspace-a",
        revision=12,
        workspace_revision=3,
        status="committed",
    )
    states.set_provider("openai", revision=5, state="active", credential_id="credential-a")

    lease = WorkspaceCredentialGate(states, FakeCredentials()).resolve(
        LockedWorkspace("workspace-a", 3),
        "openai",
    )

    assert lease.workspace_revision == 3
    assert lease.migration_revision == 12


def test_validate_rejects_revision_change_before_provider_client_construction():
    states = InMemoryWorkspaceCredentialState()
    states.set_migration(
        "workspace-a",
        revision=12,
        workspace_revision=3,
        status="committed",
    )
    states.set_provider("openai", revision=5, state="active", credential_id="credential-a")
    gate = WorkspaceCredentialGate(states, FakeCredentials())
    workspace = LockedWorkspace("workspace-a", 3)
    lease = gate.resolve(workspace, "openai")

    states.set_provider("openai", revision=6, state="active", credential_id="credential-b")

    with pytest.raises(CredentialGateError, match="credential_revision_changed"):
        gate.validate(workspace, "openai", lease)


def test_validate_rejects_persisted_workspace_revision_change_before_client_construction():
    states = InMemoryWorkspaceCredentialState()
    states.set_migration(
        "workspace-a",
        revision=12,
        workspace_revision=3,
        status="committed",
    )
    states.set_provider("openai", revision=5, state="active", credential_id="credential-a")
    gate = WorkspaceCredentialGate(states, FakeCredentials())
    workspace = LockedWorkspace("workspace-a", 3)
    lease = gate.resolve(workspace, "openai")

    states.set_migration(
        "workspace-a",
        revision=12,
        workspace_revision=4,
        status="committed",
    )

    with pytest.raises(CredentialGateError, match="credential_revision_changed"):
        gate.validate(workspace, "openai", lease)


class FakeJournalStore:
    def __init__(self):
        self.value = type(
            "Journal",
            (),
            {
                "revision": 9,
                "workspace_revision": 4,
                "status": "committed",
            },
        )()

    def load(self, identity: str):
        return self.value if identity == "workspace-a" else None


class FakeConfigStore:
    def load(self, provider: str):
        if provider != "openai":
            raise AssertionError("unexpected provider")
        return type(
            "Config",
            (),
            {
                "revision": 7,
                "credential_state": "active",
                "active_credential_id": "credential-a",
            },
        )()


def test_persistent_state_adapter_maps_journal_and_provider_config():
    assert hasattr(gate_module, "PersistentWorkspaceCredentialState")
    states = gate_module.PersistentWorkspaceCredentialState(FakeJournalStore(), FakeConfigStore())

    assert states.migration("workspace-a") == MigrationState(9, 4, "committed")
    assert states.provider("openai") == ProviderState(7, "active", "credential-a")
