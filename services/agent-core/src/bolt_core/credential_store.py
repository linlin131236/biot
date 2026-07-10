from typing import Protocol


class CredentialStore(Protocol):
    def save(self, credential_id: str, secret: str) -> None: ...

    def load(self, credential_id: str) -> str | None: ...

    def delete(self, credential_id: str) -> None: ...

    def exists(self, credential_id: str) -> bool: ...


class InMemoryCredentialStore:
    def __init__(self, values: dict[str, str] | None = None) -> None:
        self._values: dict[str, str] = {}
        for credential_id, secret in (values or {}).items():
            self.save(credential_id, secret)

    def save(self, credential_id: str, secret: str) -> None:
        if not credential_id or not secret:
            raise ValueError("credential id and secret are required")
        self._values[credential_id] = secret

    def load(self, credential_id: str) -> str | None:
        return self._values.get(credential_id)

    def delete(self, credential_id: str) -> None:
        self._values.pop(credential_id, None)

    def exists(self, credential_id: str) -> bool:
        return credential_id in self._values
