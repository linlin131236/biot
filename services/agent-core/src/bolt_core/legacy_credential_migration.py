"""Fail-closed migration of one selected workspace's legacy plaintext key."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
import json
from pathlib import Path
from typing import Protocol
from uuid import uuid4

from bolt_core.atomic_write import atomic_write_json
from bolt_core.credential_lifecycle import CredentialConfig


class MigrationError(RuntimeError):
    pass


@dataclass(frozen=True)
class MigrationJournal:
    status: str
    workspace_identity: str
    workspace_revision: int
    revision: int
    schema_version: int = 1
    attempt_id: str | None = None
    credential_id: str | None = None
    created_by_attempt: bool = False
    legacy_volume_serial: int | None = None
    legacy_file_id: str | None = None


class MigrationFiles(Protocol):
    def open_selected(self, workspace: Path) -> object | None: ...
    def read_bounded(self, reference: object, limit: int) -> bytes: ...
    def delete_verified(self, reference: object) -> None: ...
    def close(self, reference: object) -> None: ...


class MigrationJournalStore(Protocol):
    def load(self, identity: str) -> MigrationJournal | None: ...
    def save(self, journal: MigrationJournal) -> MigrationJournal: ...


class JsonMigrationJournal:
    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)

    def load(self, identity: str) -> MigrationJournal | None:
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return None
        except (OSError, json.JSONDecodeError, TypeError) as error:
            raise MigrationError("credential_migration_failed") from error
        raw = data.get(identity)
        if raw is None:
            return None
        try:
            return MigrationJournal(**raw)
        except TypeError as error:
            raise MigrationError("credential_migration_failed") from error

    def save(self, journal: MigrationJournal) -> MigrationJournal:
        current = self.load(journal.workspace_identity)
        saved = replace(journal, revision=1 if current is None else current.revision + 1)
        try:
            data = json.loads(self._path.read_text(encoding="utf-8")) if self._path.exists() else {}
            data[saved.workspace_identity] = asdict(saved)
            atomic_write_json(self._path, data)
        except (OSError, json.JSONDecodeError, TypeError) as error:
            raise MigrationError("credential_migration_failed") from error
        return saved


class InMemoryMigrationJournal:
    def __init__(self) -> None:
        self._values: dict[str, MigrationJournal] = {}

    def load(self, identity: str) -> MigrationJournal | None:
        return self._values.get(identity)

    def save(self, journal: MigrationJournal) -> MigrationJournal:
        current = self._values.get(journal.workspace_identity)
        saved = replace(journal, revision=1 if current is None else current.revision + 1)
        self._values[saved.workspace_identity] = saved
        return saved


class LegacyCredentialMigration:
    def __init__(self, files: MigrationFiles, journals: MigrationJournalStore) -> None:
        self._files = files
        self._journals = journals

    def migrate_selected(
        self,
        *,
        selected_workspace: Path,
        workspace_identity: str,
        workspace_revision: int,
        provider: str,
        credentials,
        configs,
        credential_id: str,
    ) -> str:
        journal = self._journals.load(workspace_identity)
        if journal is not None:
            self._validate_journal(journal, workspace_revision)
            return self._resume(journal, selected_workspace, provider, credentials, configs)
        reference = self._files.open_selected(selected_workspace)
        if reference is None:
            self._save("committed", workspace_identity, workspace_revision)
            return "absent"
        try:
            config = configs.load(provider)
            if config.credential_state == "active" and config.active_credential_id:
                self._save("additional_legacy_key", workspace_identity, workspace_revision)
                raise MigrationError("credential_migration_additional_legacy_key")
            if config.credential_state != "absent":
                self._save("failed", workspace_identity, workspace_revision)
                raise MigrationError("credential_migration_failed")
            return self._migrate_reference(
                reference, workspace_identity, workspace_revision, provider,
                credentials, configs, credential_id, config,
            )
        finally:
            self._files.close(reference)

    def _resume(self, journal, workspace, provider, credentials, configs) -> str:
        if journal.status == "committed":
            return self._check_committed(journal, workspace, provider, configs)
        if journal.status == "committed_cleanup_required":
            return self._retry_cleanup(journal, workspace, provider, credentials, configs)
        if journal.status == "additional_legacy_key":
            raise MigrationError("credential_migration_additional_legacy_key")
        if journal.status == "pending":
            self._journals.save(replace(journal, status="recovery_required"))
        raise MigrationError("credential_migration_failed")

    def _check_committed(self, journal, workspace, provider, configs) -> str:
        reference = self._files.open_selected(workspace)
        if reference is None:
            return "committed"
        try:
            config = configs.load(provider)
            if config.credential_state == "active" and config.active_credential_id:
                self._journals.save(replace(journal, status="additional_legacy_key"))
                raise MigrationError("credential_migration_additional_legacy_key")
            raise MigrationError("credential_migration_failed")
        finally:
            self._files.close(reference)

    def _migrate_reference(self, reference, identity, workspace_revision, provider, credentials, configs, credential_id, original) -> str:
        secret = self._read_secret(reference)
        journal = self._save("pending", identity, workspace_revision, credential_id=credential_id, reference=reference)
        created = False
        try:
            existing = credentials.load(credential_id)
            if existing is None:
                credentials.save(credential_id, secret)
                created = True
                journal = self._journals.save(replace(journal, created_by_attempt=True))
            elif existing != secret:
                self._journals.save(replace(journal, status="conflict"))
                raise MigrationError("credential_migration_conflict")
            if credentials.load(credential_id) != secret:
                raise MigrationError("credential_read_failed")
            pending = configs.save(
                provider,
                CredentialConfig(
                    credential_state="credential_switch_pending",
                    pending_credential_id=credential_id,
                    attempt_id=journal.attempt_id,
                ),
                original.revision,
            )
            if configs.load(provider) != pending or credentials.load(credential_id) != secret:
                raise MigrationError("credential_revision_changed")
            active = configs.save(
                provider,
                CredentialConfig(credential_state="active", active_credential_id=credential_id),
                pending.revision,
            )
            if configs.load(provider) != active or credentials.load(credential_id) != secret:
                raise MigrationError("credential_revision_changed")
            cleanup = self._journals.save(replace(journal, status="committed_cleanup_required"))
        except MigrationError as error:
            if str(error) == "credential_migration_conflict":
                raise
            self._compensate(provider, configs, credentials, original, journal, created)
            raise
        except BaseException as error:
            self._compensate(provider, configs, credentials, original, journal, created)
            raise MigrationError("credential_migration_failed") from error
        try:
            self._files.delete_verified(reference)
        except BaseException as error:
            raise MigrationError("credential_migration_failed") from error
        self._journals.save(replace(cleanup, status="committed"))
        return "migrated"

    def _retry_cleanup(self, journal, workspace, provider, credentials, configs) -> str:
        config = configs.load(provider)
        if config.credential_state != "active" or config.active_credential_id != journal.credential_id:
            raise MigrationError("credential_migration_failed")
        reference = self._files.open_selected(workspace)
        if reference is None:
            self._journals.save(replace(journal, status="committed"))
            return "migrated"
        try:
            if not self._same_reference(journal, reference):
                raise MigrationError("credential_migration_failed")
            if credentials.load(journal.credential_id) != self._read_secret(reference):
                raise MigrationError("credential_migration_failed")
            self._files.delete_verified(reference)
        except MigrationError:
            raise
        except BaseException as error:
            raise MigrationError("credential_migration_failed") from error
        finally:
            self._files.close(reference)
        self._journals.save(replace(journal, status="committed"))
        return "migrated"

    def _compensate(self, provider, configs, credentials, original, journal, created) -> None:
        try:
            current = configs.load(provider)
            if current != original:
                restored = configs.save(provider, original, current.revision)
                if configs.load(provider) != restored:
                    raise MigrationError("credential_revision_changed")
            if created:
                credentials.delete(journal.credential_id)
            self._journals.save(replace(journal, status="failed"))
        except BaseException as error:
            self._journals.save(replace(journal, status="recovery_required"))
            raise MigrationError("credential_recovery_required") from error

    def _read_secret(self, reference: object) -> str:
        content = self._files.read_bounded(reference, 2561)
        if len(content) > 2560:
            raise MigrationError("credential_secret_too_large")
        if not content:
            raise MigrationError("credential_secret_empty")
        if content.startswith(b"\xef\xbb\xbf") or b"\x00" in content:
            raise MigrationError("credential_encoding_invalid")
        try:
            secret = content.decode("utf-8", errors="strict")
        except UnicodeDecodeError as error:
            raise MigrationError("credential_encoding_invalid") from error
        if "\ufffd" in secret:
            raise MigrationError("credential_encoding_invalid")
        return secret

    def _save(self, status, identity, workspace_revision, credential_id=None, reference=None) -> MigrationJournal:
        volume, file_id = _reference_identity(reference)
        return self._journals.save(MigrationJournal(
            status, identity, workspace_revision, 0, attempt_id=str(uuid4()),
            credential_id=credential_id, legacy_volume_serial=volume, legacy_file_id=file_id,
        ))

    def _same_reference(self, journal, reference) -> bool:
        return (journal.legacy_volume_serial, journal.legacy_file_id) == _reference_identity(reference)

    def _validate_journal(self, journal, workspace_revision) -> None:
        if journal.schema_version != 1 or journal.workspace_revision != workspace_revision:
            raise MigrationError("credential_migration_failed")


def _reference_identity(reference: object | None) -> tuple[int | None, str | None]:
    if reference is None:
        return None, None
    volume = getattr(reference, "volume_serial", None)
    file_id = getattr(reference, "file_id", None)
    if not isinstance(volume, int) or not isinstance(file_id, bytes) or len(file_id) != 16:
        raise MigrationError("credential_migration_failed")
    return volume, file_id.hex()
