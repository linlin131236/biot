from dataclasses import dataclass
from pathlib import Path

import pytest

from bolt_core.credential_lifecycle import CredentialConfig, InMemoryCredentialConfigStore
from bolt_core.legacy_credential_migration import (
    InMemoryMigrationJournal,
    JsonMigrationJournal,
    LegacyCredentialMigration,
    MigrationError,
    MigrationJournal,
)


@dataclass(frozen=True)
class FakeReference:
    path: Path
    volume_serial: int = 7
    file_id: bytes = b"f" * 16
    size: int = 0


class RecordingFiles:
    def __init__(self, contents: dict[Path, bytes], *, fail_delete: bool = False):
        self.contents = dict(contents)
        self.opens: list[Path] = []
        self.reads: list[Path] = []
        self.deletes: list[Path] = []
        self.fail_delete = fail_delete

    def open_selected(self, workspace: Path) -> FakeReference | None:
        path = workspace / ".bolt" / "desktop-api-key"
        self.opens.append(path)
        if path not in self.contents:
            return None
        return FakeReference(path, size=len(self.contents[path]))

    def read_bounded(self, reference: FakeReference, limit: int) -> bytes:
        self.reads.append(reference.path)
        return self.contents[reference.path][:limit]

    def delete_verified(self, reference: FakeReference) -> None:
        self.deletes.append(reference.path)
        if self.fail_delete:
            raise OSError("delete failed")
        self.contents.pop(reference.path, None)

    def close(self, reference: FakeReference) -> None:
        pass


class MigrationCredentials:
    def __init__(self, values: dict[str, str] | None = None):
        self.values = dict(values or {})
        self.deleted: list[str] = []

    def save(self, credential_id: str, secret: str) -> None:
        self.values[credential_id] = secret

    def load(self, credential_id: str) -> str | None:
        return self.values.get(credential_id)

    def delete(self, credential_id: str) -> None:
        self.deleted.append(credential_id)
        self.values.pop(credential_id, None)


def _id() -> str:
    return "wincred.v1.00000000-0000-4000-8000-000000000001"


def _migrate(files, journals, credentials, configs, workspace: Path) -> str:
    return LegacyCredentialMigration(files, journals).migrate_selected(
        selected_workspace=workspace,
        workspace_identity="workspace-a",
        workspace_revision=1,
        provider="openai-compatible",
        credentials=credentials,
        configs=configs,
        credential_id=_id(),
    )


def test_json_journal_persists_additional_legacy_across_restart(tmp_path):
    path = tmp_path / "migration-journal.json"
    first = JsonMigrationJournal(path)
    first.save(MigrationJournal("additional_legacy_key", "workspace-b", 8, 0))

    state = JsonMigrationJournal(path).load("workspace-b")

    assert state is not None
    assert state.status == "additional_legacy_key"
    assert state.workspace_revision == 8
    assert state.revision == 1


def test_success_activates_credential_before_deleting_the_legacy_file(tmp_path):
    workspace = tmp_path / "a"
    legacy = workspace / ".bolt" / "desktop-api-key"
    files = RecordingFiles({legacy: b"synthetic-secret"})
    credentials = MigrationCredentials()
    configs = InMemoryCredentialConfigStore()

    result = _migrate(files, InMemoryMigrationJournal(), credentials, configs, workspace)

    assert result == "migrated"
    assert configs.load("openai-compatible").active_credential_id == _id()
    assert files.deletes == [legacy]
    assert credentials.values == {_id(): "synthetic-secret"}


@pytest.mark.parametrize("content, code", [
    (b"", "credential_secret_empty"),
    (b"\xef\xbb\xbfsecret", "credential_encoding_invalid"),
    (b"secret\x00", "credential_encoding_invalid"),
    (b"x" * 2561, "credential_secret_too_large"),
])
def test_rejects_invalid_legacy_bytes_without_deleting_them(tmp_path, content, code):
    workspace = tmp_path / "a"
    legacy = workspace / ".bolt" / "desktop-api-key"
    files = RecordingFiles({legacy: content})

    with pytest.raises(MigrationError, match=code):
        _migrate(files, InMemoryMigrationJournal(), MigrationCredentials(), InMemoryCredentialConfigStore(), workspace)

    assert files.deletes == []


def test_existing_different_credential_marks_conflict_without_overwriting_or_deleting(tmp_path):
    workspace = tmp_path / "a"
    legacy = workspace / ".bolt" / "desktop-api-key"
    files = RecordingFiles({legacy: b"legacy-secret"})
    credentials = MigrationCredentials({_id(): "other-secret"})
    journals = InMemoryMigrationJournal()

    with pytest.raises(MigrationError, match="credential_migration_conflict"):
        _migrate(files, journals, credentials, InMemoryCredentialConfigStore(), workspace)

    assert credentials.values == {_id(): "other-secret"}
    assert files.deletes == []
    assert journals.load("workspace-a").status == "conflict"


def test_active_provider_marks_only_selected_workspace_as_additional_without_reading(tmp_path):
    workspace = tmp_path / "a"
    legacy = workspace / ".bolt" / "desktop-api-key"
    files = RecordingFiles({legacy: b"secret-a"})
    configs = InMemoryCredentialConfigStore({
        "openai-compatible": CredentialConfig(credential_state="active", active_credential_id="existing"),
    })
    journals = InMemoryMigrationJournal()

    with pytest.raises(MigrationError, match="credential_migration_additional_legacy_key"):
        _migrate(files, journals, MigrationCredentials(), configs, workspace)

    assert files.reads == []
    assert files.deletes == []
    assert journals.load("workspace-a").status == "additional_legacy_key"


def test_absent_legacy_initializes_a_committed_workspace_gate(tmp_path):
    journals = InMemoryMigrationJournal()

    result = _migrate(RecordingFiles({}), journals, MigrationCredentials(), InMemoryCredentialConfigStore(), tmp_path / "a")

    assert result == "absent"
    assert journals.load("workspace-a").status == "committed"


def test_delete_failure_keeps_valid_credential_but_blocks_with_cleanup_state(tmp_path):
    workspace = tmp_path / "a"
    legacy = workspace / ".bolt" / "desktop-api-key"
    files = RecordingFiles({legacy: b"secret-a"}, fail_delete=True)
    journals = InMemoryMigrationJournal()
    credentials = MigrationCredentials()
    configs = InMemoryCredentialConfigStore()

    with pytest.raises(MigrationError, match="credential_migration_failed"):
        _migrate(files, journals, credentials, configs, workspace)

    assert configs.load("openai-compatible").active_credential_id == _id()
    assert credentials.values == {_id(): "secret-a"}
    assert journals.load("workspace-a").status == "committed_cleanup_required"
