from __future__ import annotations

import base64
import asyncio
from dataclasses import dataclass
import hashlib
import hmac
import json
import os
import socket
import sys
from pathlib import Path
from typing import BinaryIO, MutableMapping, Protocol


class DesktopServer(Protocol):
    async def startup(self, sockets: list[socket.socket]) -> None: ...
    async def main_loop(self) -> None: ...
    async def shutdown(self, sockets: list[socket.socket]) -> None: ...


@dataclass(frozen=True)
class StartupEnvironment:
    startup_id: str
    bootstrap_key: bytes
    bearer_token: str
    workspace: str
    data_root: str


@dataclass(frozen=True)
class DesktopSecurityContext:
    credential_lifecycle: object
    credential_configs: object
    credential_store: object
    credential_gate: object
    model_gateway: object
    locked_workspace: object


DESKTOP_WORKSPACE_REVISION = 1


async def serve_desktop_core(
    server: DesktopServer,
    sock: socket.socket,
    startup: StartupEnvironment,
    output: BinaryIO,
    *,
    pid: int,
) -> None:
    sockets = [sock]
    await server.startup(sockets=sockets)
    port = sock.getsockname()[1]
    output.write(create_readiness_line(
        startup_id=startup.startup_id,
        bootstrap_key=startup.bootstrap_key,
        pid=pid,
        port=port,
    ))
    output.flush()
    try:
        await server.main_loop()
    finally:
        await server.shutdown(sockets=sockets)


def bind_desktop_socket(port: int) -> socket.socket:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        sock.bind(("127.0.0.1", port))
        sock.listen(socket.SOMAXCONN)
        return sock
    except BaseException:
        sock.close()
        raise


def consume_startup_environment(env: MutableMapping[str, str]) -> StartupEnvironment:
    startup_id = env.pop("BOLT_CORE_STARTUP_ID")
    bootstrap_key = _decode_canonical_base64url(env.pop("BOLT_CORE_BOOTSTRAP_KEY"), 32)
    bearer_token = env.pop("BOLT_CORE_BEARER")
    workspace = env["BOLT_WORKSPACE"]
    data_root = env.pop("BOLT_CORE_DATA_ROOT")
    if env.get("BOLT_CORE_PROTOCOL_VERSION") != "1":
        raise ValueError("unsupported desktop runner protocol")
    _decode_canonical_base64url(startup_id, 32)
    _decode_canonical_base64url(bearer_token, 32)
    return StartupEnvironment(startup_id, bootstrap_key, bearer_token, workspace, data_root)


def create_readiness_line(
    *,
    startup_id: str,
    bootstrap_key: bytes,
    pid: int,
    port: int,
) -> bytes:
    transcript = (
        f"bolt-core-ready-v1\n{startup_id}\n{pid}\n127.0.0.1\n{port}\n"
    ).encode("utf-8")
    proof = _encode_base64url(hmac.new(bootstrap_key, transcript, hashlib.sha256).digest())
    payload = {
        "type": "bolt.core.ready",
        "version": 1,
        "startup_id": startup_id,
        "pid": pid,
        "host": "127.0.0.1",
        "port": port,
        "proof": proof,
    }
    return json.dumps(payload, ensure_ascii=True, separators=(",", ":")).encode("utf-8") + b"\n"


def _encode_base64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _decode_canonical_base64url(value: str, expected_length: int) -> bytes:
    if not value or "=" in value:
        raise ValueError("invalid base64url value")
    try:
        raw = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
    except (ValueError, base64.binascii.Error) as error:
        raise ValueError("invalid base64url value") from error
    if len(raw) != expected_length or _encode_base64url(raw) != value:
        raise ValueError("invalid base64url value")
    return raw


def stable_workspace_identity(workspace: str | Path) -> str:
    normalized = os.path.normcase(os.path.abspath(os.fspath(workspace)))
    digest = hashlib.sha256(f"bolt-workspace-v1\0{normalized}".encode("utf-8")).hexdigest()
    return f"workspace.v1.{digest}"


def build_desktop_security_context(workspace: str | Path, credentials) -> DesktopSecurityContext:
    from bolt_core.credential_lifecycle import CredentialLifecycle, JsonCredentialConfigStore
    from bolt_core.legacy_credential_migration import JsonMigrationJournal, LegacyCredentialMigration
    from bolt_core.model_gateway import DefaultModelGateway
    from bolt_core.windows_credential_manager import new_credential_id
    from bolt_core.windows_legacy_secret_file import WindowsLegacySecretFiles
    from bolt_core.workspace_credential_gate import (
        LockedWorkspace,
        PersistentWorkspaceCredentialState,
        WorkspaceCredentialGate,
    )

    root = Path(os.path.abspath(os.fspath(workspace)))
    configs = JsonCredentialConfigStore(root / ".bolt" / "credential-state.json")
    journals = JsonMigrationJournal(root / ".bolt" / "credential-migration.json")
    identity = stable_workspace_identity(root)
    binding = LockedWorkspace(identity, DESKTOP_WORKSPACE_REVISION)
    LegacyCredentialMigration(WindowsLegacySecretFiles(), journals).migrate_selected(
        selected_workspace=root,
        workspace_identity=identity,
        workspace_revision=binding.revision,
        provider="openai-compatible",
        credentials=credentials,
        configs=configs,
        credential_id=new_credential_id(),
    )
    gate = WorkspaceCredentialGate(PersistentWorkspaceCredentialState(journals, configs), credentials)
    lifecycle = CredentialLifecycle(credentials, configs, id_factory=new_credential_id)
    return DesktopSecurityContext(
        lifecycle,
        configs,
        credentials,
        gate,
        DefaultModelGateway(credential_gate=gate),
        binding,
    )


def main() -> None:
    import uvicorn

    from bolt_core.app import create_app
    from bolt_core.windows_credential_manager import Advapi32CredentialApi, WindowsCredentialManagerStore

    startup = consume_startup_environment(os.environ)
    sock = bind_desktop_socket(0)
    security = build_desktop_security_context(
        startup.workspace,
        WindowsCredentialManagerStore(Advapi32CredentialApi()),
    )
    config = uvicorn.Config(
        create_app(
            local_api_token=startup.bearer_token,
            require_local_api_token=True,
            project_dir=startup.workspace,
            persistence_root=startup.data_root,
            lock_default_workspace=True,
            desktop_production=True,
            credential_lifecycle=security.credential_lifecycle,
            credential_configs=security.credential_configs,
            credential_store=security.credential_store,
            model_gateway=security.model_gateway,
            locked_workspace_binding=security.locked_workspace,
        ),
        host="127.0.0.1",
        log_config=None,
        access_log=False,
    )
    server = uvicorn.Server(config)
    config.load()
    server.lifespan = config.lifespan_class(config)
    asyncio.run(serve_desktop_core(server, sock, startup, sys.stdout.buffer, pid=os.getpid()))


if __name__ == "__main__":
    main()
