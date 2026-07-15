"""Core-owned Runtime control plane with no Renderer or Runtime authority leaks."""

from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import RLock
from typing import Callable, Iterable
from uuid import uuid4

from bolt_core.model_settings import ModelSettingsStore
from bolt_core.runtime.contracts import RuntimeCapabilities, RuntimeSession
from bolt_core.runtime.events import RuntimeEvent, RuntimeEventKind, RuntimeEventStream
from bolt_core.runtime.model_access import RuntimeModelPolicy
from bolt_core.runtime.workspace_projection import WorkspaceProjectionError
from bolt_core.runtime.hermes_release_catalog import HermesReleaseCatalog, HermesReleaseUnavailable


class RuntimeControlPlaneError(RuntimeError):
    pass


class RuntimeUnavailableError(RuntimeControlPlaneError):
    pass


class RuntimeNotFoundError(RuntimeControlPlaneError):
    pass


class RuntimeControlPlane:
    """Coordinate Runtime lifecycle without exposing its internal authority."""

    def __init__(
        self,
        *,
        registry,
        manager,
        repository,
        workspace_id: str,
        broker,
        supervisor,
        catalog: HermesReleaseCatalog | None = None,
        managed_runtime_root: Path | None = None,
        bundled_runtime_root: Path | None = None,
        profile_gateway=None,
        startable_runtime_ids: Iterable[str] = (),
        hermes_factory: Callable[[object], object] | None = None,
    ) -> None:
        self._registry = registry
        self._manager = manager
        self._repository = repository
        self._workspace_id = workspace_id
        self._broker = broker
        self._supervisor = supervisor
        self._catalog = catalog or HermesReleaseCatalog.bundled()
        self._managed_root = Path(managed_runtime_root) if managed_runtime_root is not None else None
        self._bundled_root = Path(bundled_runtime_root) if bundled_runtime_root is not None else None
        self._profile_gateway = profile_gateway
        self._startable_runtime_ids = set(startable_runtime_ids)
        self._hermes_factory = hermes_factory
        self._hermes_registration_error: str | None = None
        self._event_lock = RLock()

    def list_runtimes(self) -> list[dict]:
        runtime_ids = {descriptor.runtime_id for descriptor in self._registry.descriptors()}
        runtime_ids.add("hermes")
        return [self.runtime_status(runtime_id) for runtime_id in sorted(runtime_ids)]

    def runtime_status(self, runtime_id: str) -> dict:
        if runtime_id == "hermes":
            return self._hermes_status()
        try:
            descriptor = self._registry.descriptor(runtime_id)
        except ValueError as error:
            raise RuntimeNotFoundError("runtime_not_found") from error
        return {
            "runtime_id": descriptor.runtime_id,
            "implementation_version": descriptor.implementation_version,
            "protocol_type": descriptor.protocol_type,
            "protocol_version": descriptor.protocol_version,
            "capabilities": asdict(descriptor.capabilities),
            "state": "available",
            "start_available": descriptor.runtime_id in self._startable_runtime_ids,
            "blocked_reason": (
                None if descriptor.runtime_id in self._startable_runtime_ids else "runtime_controlled_by_harness"
            ),
            "active_session_count": sum(
                session.runtime_id == descriptor.runtime_id for session in self._manager.sessions()
            ),
        }

    def capabilities(self, runtime_id: str) -> dict:
        status = self.runtime_status(runtime_id)
        return {
            "runtime_id": status["runtime_id"],
            "state": status["state"],
            "capabilities": status["capabilities"],
        }

    def verify_hermes_installation(self) -> dict:
        try:
            release = self._catalog.release()
        except HermesReleaseUnavailable:
            return {"runtime_id": "hermes", "state": "release_unavailable"}
        if self._managed_root is None:
            return {"runtime_id": "hermes", "state": "release_unavailable"}
        installation = self._managed_root / "hermes" / release.manifest.implementation_version
        if not installation.is_dir():
            return {
                "runtime_id": "hermes",
                "state": "not_installed",
                "implementation_version": release.manifest.implementation_version,
            }
        try:
            release.manifest.verify_installation(
                self._managed_root, installation, require_complete_tree=True,
            )
        except ValueError:
            return {
                "runtime_id": "hermes",
                "state": "invalid",
                "implementation_version": release.manifest.implementation_version,
            }
        return {
            "runtime_id": "hermes",
            "state": "verified",
            "implementation_version": release.manifest.implementation_version,
        }

    def install_hermes(self) -> dict:
        try:
            release = self._catalog.release()
        except HermesReleaseUnavailable:
            raise RuntimeUnavailableError("release_unavailable") from None
        if self._managed_root is None or self._bundled_root is None:
            raise RuntimeUnavailableError("release_unavailable")
        source = self._bundled_root / release.artifact_relative_path
        if not source.is_dir():
            raise RuntimeUnavailableError("release_unavailable")
        import shutil

        staging = self._managed_root / ".staging" / release.manifest.implementation_version
        if staging.exists():
            raise RuntimeControlPlaneError("install_conflict")
        try:
            shutil.copytree(source, staging, symlinks=False)
            from bolt_core.runtime.hermes_installer import HermesInstaller

            HermesInstaller(self._managed_root, self._running_hermes_versions).install_release(release)
        except Exception:
            shutil.rmtree(staging, ignore_errors=True)
            raise
        installed = self.verify_hermes_installation()
        self._register_verified_hermes()
        return installed

    def start(self, runtime_id: str, task: str, mode: str) -> dict:
        status = self.runtime_status(runtime_id)
        if not status["start_available"]:
            raise RuntimeUnavailableError(status["blocked_reason"] or "runtime_start_not_available")
        task_id = f"task_{uuid4().hex}"
        try:
            session = self._manager.start(runtime_id, task_id, {"task": task, "mode": mode})
        except WorkspaceProjectionError as error:
            raise RuntimeUnavailableError("workspace_projection_required") from error
        except Exception as error:
            raise RuntimeUnavailableError("runtime_start_failed") from error
        try:
            runtime = self._registry.resolve(runtime_id)
            external_id = self._external_session_id(runtime, session)
            self._repository.create_runtime_task(
                task_id, self._workspace_id, session.session_id, runtime_id, external_id,
                {"mode": mode, "runtime_id": runtime_id},
            )
            event = RuntimeEvent(
                event_id=f"evt_{uuid4().hex}", task_id=session.task_id,
                runtime_id=session.runtime_id, session_id=session.session_id, sequence=1,
                timestamp=datetime.now(UTC), kind=RuntimeEventKind.STATUS,
                payload={"status": "running"},
            )
            self.ingest_event(session, event)
            self._manager.send(session, {"text": task})
        except Exception:
            try:
                self._manager.close(session)
            finally:
                raise
        return self.session_status(session.session_id)

    def stop(self, session_id: str) -> dict:
        session = self._owned_session(session_id)
        try:
            # Persisting the terminal event notifies the manager's session
            # revoker before cancellation reaches the adapter.
            self._ensure_terminal_event(session, RuntimeEventKind.CANCELLED)
            self._manager.cancel(session)
        except Exception as error:
            self._contain_failed_session(session)
            raise RuntimeControlPlaneError("runtime_stop_failed") from error
        return {"session_id": session_id, "status": "stop_requested"}

    def session_status(self, session_id: str) -> dict:
        try:
            session = self._owned_session(session_id)
        except RuntimeNotFoundError:
            return self._persisted_session_status(session_id)
        snapshot = self._manager.snapshot(session)
        return {
            "session_id": session.session_id,
            "runtime_id": session.runtime_id,
            "status": snapshot.status,
            "last_event_sequence": snapshot.last_event_sequence,
        }

    def ingest_event(self, session: RuntimeSession, event: RuntimeEvent) -> None:
        with self._event_lock:
            self._validate_event(session, event)
            status = _status_for_event(event)
            try:
                self._repository.append_runtime_event_with_status(
                    event.event_id, session.session_id, event.sequence, event.kind.value,
                    event.to_dict()["payload"], status,
                )
                self._manager.append_event(session, event)
            except Exception:
                self._contain_failed_session(session)
                raise

    def runtime_terminal(self, session: RuntimeSession, kind: RuntimeEventKind) -> None:
        if kind not in {
            RuntimeEventKind.COMPLETED, RuntimeEventKind.FAILED, RuntimeEventKind.CANCELLED,
        }:
            raise ValueError("runtime terminal event is invalid")
        with self._event_lock:
            snapshot = self._manager.snapshot(session)
            if snapshot.lifecycle.value != "running":
                return
            stream = RuntimeEventStream(session.task_id, session.runtime_id, session.session_id)
            for event in snapshot.events:
                stream.append(event)
            in_flight = stream.in_flight()
            payload = (
                {"summary": "Runtime completed"}
                if kind is RuntimeEventKind.COMPLETED
                else {
                    "abandoned_tool_ids": in_flight["tool_ids"],
                    "abandoned_approval_ids": in_flight["approval_ids"],
                }
            )
            if kind is RuntimeEventKind.FAILED:
                payload["error_code"] = "crashed"
            event = RuntimeEvent(
                event_id=f"evt_{uuid4().hex}", task_id=session.task_id,
                runtime_id=session.runtime_id, session_id=session.session_id,
                sequence=snapshot.last_event_sequence + 1, timestamp=datetime.now(UTC),
                kind=kind, payload=payload,
            )
            self.ingest_event(session, event)

    def test_default_profile(self) -> dict:
        if self._profile_gateway is None:
            return {"profile_id": ModelSettingsStore.PROFILE_ID, "status": "credential_unavailable"}
        try:
            self._profile_gateway.complete(ModelSettingsStore.PROFILE_ID, {
                "path": "/v1/chat/completions",
                "payload": {"messages": [{"role": "user", "content": "Reply with pong."}]},
            })
        except ValueError:
            return {"profile_id": ModelSettingsStore.PROFILE_ID, "status": "credential_unavailable"}
        except TimeoutError:
            return {"profile_id": ModelSettingsStore.PROFILE_ID, "status": "timeout"}
        except RuntimeError as error:
            status = (
                "credential_unavailable" if str(error) == "model_not_found" else "provider_error"
            )
            return {"profile_id": ModelSettingsStore.PROFILE_ID, "status": status}
        except Exception:
            return {"profile_id": ModelSettingsStore.PROFILE_ID, "status": "provider_error"}
        return {"profile_id": ModelSettingsStore.PROFILE_ID, "status": "passed"}

    def model_policy(self, session: RuntimeSession) -> RuntimeModelPolicy:
        if not isinstance(session, RuntimeSession) or self._repository is None:
            raise RuntimeUnavailableError("runtime_model_access_unavailable")
        try:
            profile = self._repository.load_model_profile(ModelSettingsStore.PROFILE_ID)
        except Exception as error:
            raise RuntimeUnavailableError("model_profile_unavailable") from error
        generation = profile.get("revision")
        context_window = profile.get("context_window")
        if (
            type(generation) is not int or generation < 0
            or type(context_window) is not int or context_window <= 0
        ):
            raise RuntimeUnavailableError("model_profile_unavailable")
        return RuntimeModelPolicy(
            model_profile_id=ModelSettingsStore.PROFILE_ID,
            allowed_paths=("/v1/chat/completions",),
            budget=32,
            expires_at=datetime.now(UTC) + timedelta(minutes=5),
            generation=generation,
            context_window=context_window,
        )

    def model_grant(self, session: RuntimeSession):
        if self._broker is None:
            raise RuntimeUnavailableError("runtime_model_access_unavailable")
        policy = self.model_policy(session)
        return self._broker.issue(session, policy)

    def startup(self) -> None:
        self._register_verified_hermes()
        if self._broker is not None:
            self._broker.start()

    def shutdown(self) -> None:
        self._manager.shutdown()
        self._supervisor.stop_all(timeout=1)
        if self._broker is not None:
            self._broker.stop()

    def _register_verified_hermes(self) -> None:
        if self._hermes_factory is None or "hermes" in self._startable_runtime_ids:
            return
        try:
            release = self._catalog.release()
            if self.verify_hermes_installation().get("state") != "verified":
                return
            required = "bin/Lib/site-packages/acp_adapter/bolt_model_client.py"
            if required not in {item.relative_path for item in release.manifest.files}:
                self._hermes_registration_error = "managed_model_bridge_unavailable"
                return
            runtime = self._hermes_factory(release)
            self._registry.register(runtime.descriptor, runtime)
        except Exception:
            self._hermes_registration_error = "managed_model_bridge_unavailable"
            return
        self._startable_runtime_ids.add("hermes")

    def _hermes_status(self) -> dict:
        if "hermes" in self._startable_runtime_ids:
            descriptor = self._registry.descriptor("hermes")
            return {
                "runtime_id": descriptor.runtime_id,
                "implementation_version": descriptor.implementation_version,
                "protocol_type": descriptor.protocol_type,
                "protocol_version": descriptor.protocol_version,
                "capabilities": asdict(descriptor.capabilities),
                "state": "available",
                "start_available": True,
                "blocked_reason": None,
                "active_session_count": sum(
                    session.runtime_id == "hermes" for session in self._manager.sessions()
                ),
            }
        verification = self.verify_hermes_installation()
        state = verification["state"]
        return {
            "runtime_id": "hermes",
            "implementation_version": verification.get("implementation_version"),
            "protocol_type": "acp",
            "protocol_version": "v1",
            "capabilities": asdict(RuntimeCapabilities()),
            "state": state,
            "start_available": False,
            "blocked_reason": (
                self._hermes_registration_error or "workspace_projection_required"
                if state == "verified" else state
            ),
            "active_session_count": sum(
                session.runtime_id == "hermes" for session in self._manager.sessions()
            ),
        }

    def _owned_session(self, session_id: str) -> RuntimeSession:
        for session in self._manager.sessions(include_closed=True):
            if session.session_id == session_id:
                return session
        raise RuntimeNotFoundError("runtime_session_not_found")

    def _persisted_session_status(self, session_id: str) -> dict:
        if self._repository is None:
            raise RuntimeNotFoundError("runtime_session_not_found")
        for record in self._repository.list_runtime_sessions(self._workspace_id):
            if record["id"] == session_id:
                return {
                    "session_id": record["id"],
                    "runtime_id": record["runtime_id"],
                    "status": record["status"],
                    "last_event_sequence": len(self._repository.list_runtime_events(session_id)),
                }
        raise RuntimeNotFoundError("runtime_session_not_found")

    def _validate_event(self, session: RuntimeSession, event: RuntimeEvent) -> None:
        snapshot = self._manager.snapshot(session)
        preview = RuntimeEventStream(session.task_id, session.runtime_id, session.session_id)
        for existing in snapshot.events:
            preview.append(existing)
        preview.append(event)

    def _ensure_terminal_event(self, session: RuntimeSession, kind: RuntimeEventKind) -> None:
        snapshot = self._manager.snapshot(session)
        if snapshot.lifecycle.value != "running":
            return
        in_flight = {"tool_ids": [], "approval_ids": []}
        if snapshot.events:
            stream = RuntimeEventStream(session.task_id, session.runtime_id, session.session_id)
            for event in snapshot.events:
                stream.append(event)
            in_flight = stream.in_flight()
        event = RuntimeEvent(
            event_id=f"evt_{uuid4().hex}", task_id=session.task_id, runtime_id=session.runtime_id,
            session_id=session.session_id, sequence=snapshot.last_event_sequence + 1,
            timestamp=datetime.now(UTC), kind=kind,
            payload={
                "abandoned_tool_ids": in_flight["tool_ids"],
                "abandoned_approval_ids": in_flight["approval_ids"],
            },
        )
        self.ingest_event(session, event)

    def _mark_crashed(self, session: RuntimeSession) -> None:
        try:
            snapshot = self._manager.snapshot(session)
            if snapshot.lifecycle.value == "running":
                self._manager.mark_crashed(session)
        finally:
            if self._broker is not None:
                self._broker.revoke_session(session)

    def _contain_failed_session(self, session: RuntimeSession) -> None:
        try:
            self._manager.close(session)
        except Exception:
            if self._broker is not None:
                self._broker.revoke_session(session)

    def _running_hermes_versions(self) -> set[str]:
        return {
            self._manager.snapshot(session).implementation_version
            for session in self._manager.sessions()
            if session.runtime_id == "hermes"
        }

    @staticmethod
    def _external_session_id(runtime, session: RuntimeSession) -> str:
        provider = getattr(runtime, "external_session_id", None)
        if not callable(provider):
            return session.session_id
        value = provider(session)
        if not isinstance(value, str) or not value:
            raise ValueError("runtime external session identifier is invalid")
        return value


def _status_for_event(event: RuntimeEvent) -> str:
    if event.kind is RuntimeEventKind.COMPLETED:
        return "completed"
    if event.kind is RuntimeEventKind.FAILED:
        return "failed"
    if event.kind is RuntimeEventKind.CANCELLED:
        return "cancelled"
    if event.kind is RuntimeEventKind.STATUS:
        return str(event.payload["status"])
    if event.kind is RuntimeEventKind.APPROVAL_REQUESTED:
        return "waiting_approval"
    return "running"
