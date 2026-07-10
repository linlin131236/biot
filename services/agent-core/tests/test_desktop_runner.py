import base64
import hashlib
import hmac
import json

import socket

import asyncio
import io
import os
import subprocess
import sys

import httpx
import pytest
import bolt_core.desktop_runner as desktop_runner
from bolt_core.credential_lifecycle import CredentialConfig, JsonCredentialConfigStore
from bolt_core.legacy_credential_migration import JsonMigrationJournal, MigrationError, MigrationJournal

from bolt_core.desktop_runner import (
    StartupEnvironment,
    bind_desktop_socket,
    consume_startup_environment,
    create_readiness_line,
    serve_desktop_core,
)


def b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def test_module_entrypoint_emits_proof_and_serves_authenticated_core(tmp_path):
    startup_id = b64url(b"s" * 32)
    bootstrap = b64url(b"k" * 32)
    bearer = b64url(b"b" * 32)
    env = {
        "SystemRoot": os.environ["SystemRoot"],
        "WINDIR": os.environ["WINDIR"],
        "TEMP": os.environ["TEMP"],
        "TMP": os.environ["TMP"],
        "PATH": os.environ.get("PATH", ""),
        "PYTHONPATH": str((tmp_path.parent / "unused")),
        "BOLT_CORE_STARTUP_ID": startup_id,
        "BOLT_CORE_BOOTSTRAP_KEY": bootstrap,
        "BOLT_CORE_BEARER": bearer,
        "BOLT_WORKSPACE": str(tmp_path),
        "BOLT_CORE_PROTOCOL_VERSION": "1",
    }
    source_root = os.path.join(os.path.dirname(__file__), "..", "src")
    env["PYTHONPATH"] = os.path.abspath(source_root)
    process = subprocess.Popen(
        [sys.executable, "-m", "bolt_core.desktop_runner"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )
    try:
        assert process.stdout is not None
        raw_proof = process.stdout.readline()
        if not raw_proof:
            assert process.stderr is not None
            raise AssertionError(process.stderr.read().decode("utf-8", errors="replace"))
        proof = json.loads(raw_proof)
        assert proof["startup_id"] == startup_id
        with httpx.Client(trust_env=False, timeout=5) as client:
            response = client.get(f"http://127.0.0.1:{proof['port']}/health")
            assert response.status_code == 200
            protected = client.get(
                f"http://127.0.0.1:{proof['port']}/memory",
                headers={"Authorization": f"Bearer {bearer}"},
            )
            assert protected.status_code == 200
    finally:
        process.terminate()
        process.wait(timeout=5)


def test_hands_prebound_socket_to_server_and_emits_proof_only_after_startup():
    events: list[str] = []
    output = io.BytesIO()

    class FakeServer:
        started = False
        should_exit = False

        async def startup(self, sockets):
            assert len(sockets) == 1
            assert sockets[0].getsockname()[0] == "127.0.0.1"
            self.started = True
            events.append("startup")

        async def main_loop(self):
            events.append("main_loop")

        async def shutdown(self, sockets):
            assert len(sockets) == 1
            events.append("shutdown")

    startup = StartupEnvironment(
        startup_id=b64url(b"s" * 32),
        bootstrap_key=b"k" * 32,
        bearer_token=b64url(b"b" * 32),
        workspace="D:/Projects/Bolt",
    )
    sock = bind_desktop_socket(0)
    port = sock.getsockname()[1]
    try:
        asyncio.run(serve_desktop_core(FakeServer(), sock, startup, output, pid=1234))
    finally:
        sock.close()

    assert events == ["startup", "main_loop", "shutdown"]
    assert json.loads(output.getvalue())["port"] == port


def test_binds_loopback_on_an_os_assigned_port_with_windows_exclusive_use():
    sock = bind_desktop_socket(0)
    try:
        host, port = sock.getsockname()
        assert host == "127.0.0.1"
        assert 0 < port < 65536
        assert sock.getsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE) == 1
    finally:
        sock.close()


def test_explicit_port_collision_fails_instead_of_adopting_the_listener():
    first = bind_desktop_socket(0)
    try:
        port = first.getsockname()[1]
        try:
            bind_desktop_socket(port)
        except OSError:
            pass
        else:
            raise AssertionError("occupied desktop port was adopted")
    finally:
        first.close()


def test_consumes_current_generation_secrets_and_removes_them_from_environment():
    env = {
        "BOLT_CORE_STARTUP_ID": b64url(b"s" * 32),
        "BOLT_CORE_BOOTSTRAP_KEY": b64url(b"k" * 32),
        "BOLT_CORE_BEARER": b64url(b"b" * 32),
        "BOLT_WORKSPACE": "D:/Projects/Bolt",
        "BOLT_CORE_PROTOCOL_VERSION": "1",
    }

    startup = consume_startup_environment(env)

    assert startup.startup_id == b64url(b"s" * 32)
    assert startup.bootstrap_key == b"k" * 32
    assert startup.bearer_token == b64url(b"b" * 32)
    assert startup.workspace == "D:/Projects/Bolt"
    assert "BOLT_CORE_STARTUP_ID" not in env
    assert "BOLT_CORE_BOOTSTRAP_KEY" not in env
    assert "BOLT_CORE_BEARER" not in env


def test_readiness_line_is_canonical_single_line_hmac_proof():
    startup_id = b64url(b"s" * 32)
    line = create_readiness_line(
        startup_id=startup_id,
        bootstrap_key=b"k" * 32,
        pid=1234,
        port=43123,
    )

    assert line.endswith(b"\n")
    assert line.count(b"\n") == 1
    payload = json.loads(line)
    assert set(payload) == {"type", "version", "startup_id", "pid", "host", "port", "proof"}
    transcript = f"bolt-core-ready-v1\n{startup_id}\n1234\n127.0.0.1\n43123\n".encode()
    expected = hmac.new(b"k" * 32, transcript, hashlib.sha256).digest()
    assert payload == {
        "type": "bolt.core.ready",
        "version": 1,
        "startup_id": startup_id,
        "pid": 1234,
        "host": "127.0.0.1",
        "port": 43123,
        "proof": b64url(expected),
    }


class FakeCredentialStore:
    def __init__(self, values: dict[str, str]):
        self.values = values

    def save(self, credential_id: str, secret: str) -> None:
        self.values[credential_id] = secret

    def load(self, credential_id: str) -> str | None:
        return self.values.get(credential_id)

    def delete(self, credential_id: str) -> None:
        self.values.pop(credential_id, None)


def test_desktop_security_context_reloads_persisted_workspace_gate(tmp_path):
    assert hasattr(desktop_runner, "stable_workspace_identity")
    assert hasattr(desktop_runner, "build_desktop_security_context")
    identity = desktop_runner.stable_workspace_identity(tmp_path)
    credential_id = "wincred.v1.00000000-0000-4000-8000-000000000001"
    configs = JsonCredentialConfigStore(tmp_path / ".bolt" / "credential-state.json")
    configs.save(
        "openai-compatible",
        CredentialConfig(credential_state="active", active_credential_id=credential_id),
        0,
    )
    journals = JsonMigrationJournal(tmp_path / ".bolt" / "credential-migration.json")
    journals.save(MigrationJournal("committed", identity, 1, 0))
    credentials = FakeCredentialStore({credential_id: "short-lived-secret"})

    first = desktop_runner.build_desktop_security_context(tmp_path, credentials)
    restarted = desktop_runner.build_desktop_security_context(tmp_path, credentials)

    assert first.locked_workspace == restarted.locked_workspace
    assert restarted.locked_workspace.identity == identity
    assert restarted.locked_workspace.revision == 1
    assert restarted.credential_gate.resolve(
        restarted.locked_workspace,
        "openai-compatible",
    ).secret == "short-lived-secret"


def test_persisted_journal_cannot_choose_server_locked_workspace_revision(tmp_path):
    identity = desktop_runner.stable_workspace_identity(tmp_path)
    journals = JsonMigrationJournal(tmp_path / ".bolt" / "credential-migration.json")
    journals.save(MigrationJournal("committed", identity, 99, 0))

    with pytest.raises(MigrationError, match="credential_migration_failed"):
        desktop_runner.build_desktop_security_context(tmp_path, FakeCredentialStore({}))


def test_desktop_security_context_migrates_only_its_selected_legacy_key(tmp_path):
    legacy = tmp_path / ".bolt" / "desktop-api-key"
    legacy.parent.mkdir()
    legacy.write_text("legacy-key", encoding="utf-8")
    credentials = FakeCredentialStore({})

    context = desktop_runner.build_desktop_security_context(tmp_path, credentials)

    config = context.credential_configs.load("openai-compatible")
    journal = JsonMigrationJournal(tmp_path / ".bolt" / "credential-migration.json").load(
        context.locked_workspace.identity
    )
    assert config.credential_state == "active"
    assert config.active_credential_id in credentials.values
    assert credentials.values[config.active_credential_id] == "legacy-key"
    assert not legacy.exists()
    assert journal is not None and journal.status == "committed"
