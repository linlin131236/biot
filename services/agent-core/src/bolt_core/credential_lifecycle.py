from __future__ import annotations

from dataclasses import asdict, dataclass, replace
import json
from pathlib import Path
from typing import Callable, Protocol
from uuid import uuid4

from bolt_core.atomic_write import atomic_write_json


class CredentialLifecycleError(RuntimeError):
    pass


@dataclass(frozen=True)
class CredentialConfig:
    revision: int = 0
    credential_state: str = "absent"
    active_credential_id: str | None = None
    pending_credential_id: str | None = None
    attempt_id: str | None = None


class CredentialConfigStore(Protocol):
    def load(self, provider: str) -> CredentialConfig: ...
    def save(self, provider: str, config: CredentialConfig, expected_revision: int) -> CredentialConfig: ...


class CredentialStore(Protocol):
    def save(self, credential_id: str, secret: str) -> None: ...
    def load(self, credential_id: str) -> str | None: ...
    def delete(self, credential_id: str) -> None: ...


class JsonCredentialConfigStore:
    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)

    def load(self, provider: str) -> CredentialConfig:
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return CredentialConfig()
        except (OSError, json.JSONDecodeError, TypeError, ValueError) as error:
            raise CredentialLifecycleError("credential_recovery_required") from error
        raw = data.get(provider)
        if raw is None:
            return CredentialConfig()
        try:
            return CredentialConfig(**raw)
        except TypeError as error:
            raise CredentialLifecycleError("credential_recovery_required") from error

    def save(self, provider: str, config: CredentialConfig, expected_revision: int) -> CredentialConfig:
        current = self.load(provider)
        if current.revision != expected_revision:
            raise CredentialLifecycleError("credential_revision_changed")
        saved = replace(config, revision=expected_revision + 1)
        try:
            data = json.loads(self._path.read_text(encoding="utf-8")) if self._path.exists() else {}
            data[provider] = asdict(saved)
            atomic_write_json(self._path, data)
        except OSError as error:
            raise CredentialLifecycleError("credential_recovery_required") from error
        return saved


class InMemoryCredentialConfigStore:
    def __init__(self, values: dict[str, CredentialConfig] | None = None) -> None:
        self._values = dict(values or {})
        self.history: list[CredentialConfig] = []

    def load(self, provider: str) -> CredentialConfig:
        return self._values.get(provider, CredentialConfig())

    def save(self, provider: str, config: CredentialConfig, expected_revision: int) -> CredentialConfig:
        current = self.load(provider)
        if current.revision != expected_revision:
            raise CredentialLifecycleError("credential_revision_changed")
        saved = replace(config, revision=expected_revision + 1)
        self._values[provider] = saved
        self.history.append(saved)
        return saved


class CredentialLifecycle:
    def __init__(
        self,
        credentials: CredentialStore,
        configs: CredentialConfigStore,
        *,
        id_factory: Callable[[], str],
    ) -> None:
        self._credentials = credentials
        self._configs = configs
        self._id_factory = id_factory

    def delete(self, provider: str, *, expected_revision: int) -> CredentialConfig:
        current = self._configs.load(provider)
        if current.revision != expected_revision or current.credential_state != "active" or not current.active_credential_id:
            raise CredentialLifecycleError("credential_revision_changed")
        credential_id = current.active_credential_id
        deleting = self._configs.save(
            provider,
            CredentialConfig(
                credential_state="credential_deleting",
                pending_credential_id=credential_id,
                attempt_id=str(uuid4()),
            ),
            expected_revision,
        )
        if self._configs.load(provider) != deleting:
            raise CredentialLifecycleError("credential_revision_changed")
        try:
            self._credentials.delete(credential_id)
        except BaseException as error:
            raise CredentialLifecycleError("credential_delete_failed") from error
        return self._configs.save(provider, CredentialConfig(), deleting.revision)

    def replace(self, provider: str, secret: str, *, expected_revision: int) -> CredentialConfig:
        current = self._configs.load(provider)
        if current.revision != expected_revision or current.credential_state != "active" or not current.active_credential_id:
            raise CredentialLifecycleError("credential_revision_changed")
        old_id = current.active_credential_id
        new_id = self._id_factory()
        pending = self._configs.save(
            provider,
            CredentialConfig(
                credential_state="credential_switch_pending",
                active_credential_id=old_id,
                pending_credential_id=new_id,
                attempt_id=str(uuid4()),
            ),
            expected_revision,
        )
        try:
            self._credentials.save(new_id, secret)
            if self._credentials.load(new_id) != secret:
                raise CredentialLifecycleError("credential_read_failed")
            active = self._configs.save(
                provider,
                CredentialConfig(credential_state="active", active_credential_id=new_id),
                pending.revision,
            )
            if self._configs.load(provider) != active or self._credentials.load(new_id) != secret:
                raise CredentialLifecycleError("credential_read_failed")
        except BaseException:
            try:
                self._credentials.delete(new_id)
                self._configs.save(provider, current, self._configs.load(provider).revision)
            except BaseException as compensation_error:
                raise CredentialLifecycleError("credential_recovery_required") from compensation_error
            raise
        try:
            self._credentials.delete(old_id)
        except BaseException as error:
            cleanup = self._configs.save(
                provider,
                CredentialConfig(
                    credential_state="credential_cleanup_required",
                    active_credential_id=new_id,
                    pending_credential_id=old_id,
                ),
                active.revision,
            )
            raise CredentialLifecycleError("credential_cleanup_required") from error
        return active

    def add(self, provider: str, secret: str, *, expected_revision: int) -> CredentialConfig:
        current = self._configs.load(provider)
        if current.revision != expected_revision:
            raise CredentialLifecycleError("credential_revision_changed")
        credential_id = self._id_factory()
        pending = self._configs.save(
            provider,
            CredentialConfig(
                credential_state="credential_write_pending",
                pending_credential_id=credential_id,
                attempt_id=str(uuid4()),
            ),
            expected_revision,
        )
        try:
            self._credentials.save(credential_id, secret)
            if self._credentials.load(credential_id) != secret:
                raise CredentialLifecycleError("credential_read_failed")
            reloaded = self._configs.load(provider)
            if reloaded != pending:
                raise CredentialLifecycleError("credential_revision_changed")
            if self._credentials.load(credential_id) != secret:
                raise CredentialLifecycleError("credential_read_failed")
            return self._configs.save(
                provider,
                CredentialConfig(
                    credential_state="active",
                    active_credential_id=credential_id,
                ),
                pending.revision,
            )
        except BaseException as error:
            try:
                self._credentials.delete(credential_id)
                self._configs.save(provider, CredentialConfig(), pending.revision)
            except BaseException as compensation_error:
                current = self._configs.load(provider)
                recovery = CredentialConfig(
                    credential_state="credential_recovery_required",
                    pending_credential_id=credential_id,
                    attempt_id=pending.attempt_id,
                )
                if current.revision == pending.revision:
                    self._configs.save(provider, recovery, current.revision)
                raise CredentialLifecycleError("credential_recovery_required") from compensation_error
            if isinstance(error, CredentialLifecycleError):
                raise
            raise CredentialLifecycleError("credential_read_failed") from error
