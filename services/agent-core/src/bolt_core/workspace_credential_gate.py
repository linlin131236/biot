from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class CredentialGateError(RuntimeError):
    pass


@dataclass(frozen=True)
class LockedWorkspace:
    identity: str
    revision: int


@dataclass(frozen=True)
class MigrationState:
    revision: int
    workspace_revision: int
    status: str


@dataclass(frozen=True)
class ProviderState:
    revision: int
    state: str
    credential_id: str | None


@dataclass(frozen=True)
class CredentialLease:
    secret: str
    workspace_revision: int
    migration_revision: int
    provider_revision: int
    credential_id: str


class WorkspaceCredentialState(Protocol):
    def migration(self, identity: str) -> MigrationState: ...
    def provider(self, provider: str) -> ProviderState: ...


class CredentialStore(Protocol):
    def load(self, credential_id: str) -> str | None: ...


class MigrationJournalStore(Protocol):
    def load(self, identity: str): ...


class CredentialConfigStore(Protocol):
    def load(self, provider: str): ...


class InMemoryWorkspaceCredentialState:
    def __init__(self) -> None:
        self._migrations: dict[str, MigrationState] = {}
        self._providers: dict[str, ProviderState] = {}

    def set_migration(
        self,
        identity: str,
        *,
        revision: int,
        status: str,
        workspace_revision: int | None = None,
    ) -> None:
        self._migrations[identity] = MigrationState(
            revision,
            revision if workspace_revision is None else workspace_revision,
            status,
        )

    def set_provider(self, provider: str, *, revision: int, state: str, credential_id: str | None) -> None:
        self._providers[provider] = ProviderState(revision, state, credential_id)

    def migration(self, identity: str) -> MigrationState:
        if identity not in self._migrations:
            raise CredentialGateError("credential_migration_failed")
        return self._migrations[identity]

    def provider(self, provider: str) -> ProviderState:
        if provider not in self._providers:
            raise CredentialGateError("credential_not_found")
        return self._providers[provider]


class PersistentWorkspaceCredentialState:
    def __init__(self, migrations: MigrationJournalStore, providers: CredentialConfigStore) -> None:
        self._migrations = migrations
        self._providers = providers

    def migration(self, identity: str) -> MigrationState:
        try:
            journal = self._migrations.load(identity)
            if journal is None:
                raise CredentialGateError("credential_migration_failed")
            return MigrationState(journal.revision, journal.workspace_revision, journal.status)
        except CredentialGateError:
            raise
        except Exception as error:
            raise CredentialGateError("credential_migration_failed") from error

    def provider(self, provider: str) -> ProviderState:
        try:
            config = self._providers.load(provider)
            return ProviderState(config.revision, config.credential_state, config.active_credential_id)
        except Exception as error:
            raise CredentialGateError("credential_not_found") from error


class WorkspaceCredentialGate:
    def __init__(self, states: WorkspaceCredentialState, credentials: CredentialStore) -> None:
        self._states = states
        self._credentials = credentials

    def resolve(self, workspace: LockedWorkspace, provider: str) -> CredentialLease:
        migration = self._states.migration(workspace.identity)
        if migration.workspace_revision != workspace.revision:
            raise CredentialGateError("credential_revision_changed")
        if migration.status != "committed":
            if migration.status == "additional_legacy_key":
                raise CredentialGateError("credential_migration_additional_legacy_key")
            raise CredentialGateError(f"credential_migration_{migration.status}")
        provider_state = self._states.provider(provider)
        if provider_state.state != "active" or not provider_state.credential_id:
            raise CredentialGateError("credential_not_found")
        secret = self._credentials.load(provider_state.credential_id)
        if secret is None:
            raise CredentialGateError("credential_not_found")
        final_migration = self._states.migration(workspace.identity)
        final_provider = self._states.provider(provider)
        if final_migration != migration or final_provider != provider_state:
            raise CredentialGateError("credential_revision_changed")
        return CredentialLease(
            secret,
            workspace.revision,
            migration.revision,
            provider_state.revision,
            provider_state.credential_id,
        )

    def validate(self, workspace: LockedWorkspace, provider: str, lease: CredentialLease) -> None:
        migration = self._states.migration(workspace.identity)
        provider_state = self._states.provider(provider)
        expected = (
            lease.workspace_revision,
            lease.migration_revision,
            lease.provider_revision,
            lease.credential_id,
        )
        current = (
            migration.workspace_revision,
            migration.revision,
            provider_state.revision,
            provider_state.credential_id,
        )
        if (
            migration.status != "committed"
            or provider_state.state != "active"
            or workspace.revision != lease.workspace_revision
            or current != expected
        ):
            raise CredentialGateError("credential_revision_changed")
