"""Strict stdio ACP adapter for Bolt's managed Hermes runtime."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from threading import Event, Thread
from typing import Any, Callable
from uuid import uuid4

from bolt_core.runtime.acp_events import map_acp_update, prompt_usage_payload
from bolt_core.runtime.acp_stdio import AcpStdioClient
from bolt_core.runtime.model_access import RuntimeProxyGrant
from bolt_core.runtime.contracts import RuntimeCapabilities, RuntimeDescriptor, RuntimeSession
from bolt_core.runtime.events import RuntimeEvent, RuntimeEventKind
from bolt_core.runtime.hermes_manifest import HermesManifest
from bolt_core.runtime.hermes_model_bridge import HermesModelBridge
from bolt_core.runtime.model_access import RuntimeModelPolicy
from bolt_core.runtime.model_rpc import RuntimeModelRpc
from bolt_core.runtime.process_supervisor import ManagedProcessSpec, RuntimeProcessSupervisor
from bolt_core.runtime.workspace_projection import WorkspaceProjection


@dataclass
class _SessionState:
    session: RuntimeSession
    external_session_id: str
    pid: int
    client: AcpStdioClient | None
    projection: WorkspaceProjection | None = None
    prompt_complete: Event = field(default_factory=Event)
    events: list[RuntimeEvent] = field(default_factory=list)
    next_sequence: int = 1
    error: Exception | None = None
    pending_approvals: dict[str, Event] = field(default_factory=dict)
    approvals: dict[str, bool] = field(default_factory=dict)
    closing: bool = False
    terminal_notified: bool = False
    closure_notified: bool = False


class HermesAcpRuntime:
    def __init__(
        self,
        manifest: HermesManifest,
        installation: Path,
        executable_args: list[str],
        supervisor: RuntimeProcessSupervisor,
        managed_runtime_root: Path,
        workspace: Path,
        model_grant_factory: Callable[[RuntimeSession], RuntimeProxyGrant] | None = None,
        model_policy_factory: Callable[[RuntimeSession], RuntimeModelPolicy] | None = None,
        model_rpc: RuntimeModelRpc | None = None,
        on_terminal: Callable[[RuntimeSession, RuntimeEventKind], None] | None = None,
        on_session_closed: Callable[[RuntimeSession], None] | None = None,
    ) -> None:
        self._manifest = manifest
        self._installation = installation
        self._executable_args = list(executable_args)
        self._supervisor = supervisor
        self._root = managed_runtime_root
        self._workspace = workspace
        self._model_grant_factory = model_grant_factory
        if (model_policy_factory is None) != (model_rpc is None):
            raise ValueError("Core model bridge requires policy and authority")
        if model_policy_factory is not None and model_grant_factory is not None:
            raise ValueError("Core model bridge rejects legacy proxy grant")
        self._model_bridge = (
            HermesModelBridge(model_rpc, model_policy_factory)
            if model_policy_factory is not None and model_rpc is not None else None
        )
        self._on_terminal = on_terminal or (lambda _session, _kind: None)
        self._on_session_closed = on_session_closed or (lambda _session: None)
        self._states: dict[str, _SessionState] = {}
        self._pending_requests: dict[int, _SessionState] = {}
        self._descriptor = RuntimeDescriptor(
            runtime_id="hermes",
            implementation_version=manifest.implementation_version,
            protocol_type="acp",
            protocol_version=f"v{manifest.acp_protocol_version}",
            capabilities=manifest.capabilities,
        )

    @property
    def descriptor(self) -> RuntimeDescriptor:
        return self._descriptor

    def start(self, task_id: str, request: dict) -> RuntimeSession:
        if not isinstance(request, dict):
            raise ValueError("request must be an object")
        session = RuntimeSession(f"session_{uuid4().hex}", "hermes", task_id)
        executable = self._manifest.verify_installation(
            self._root, self._installation,
            require_complete_tree=self._manifest.has_complete_inventory,
        )
        grant = self._model_grant(session)
        policy = self._model_bridge.register(session) if self._model_bridge is not None else None
        state: _SessionState | None = None
        process = None
        spec = None
        try:
            spec = self._spec_for(session, executable, grant, policy.context_window if policy else None)
            process = self._supervisor.start(spec)
            client = AcpStdioClient(
                process, self._on_message, self._on_request,
                lambda error: self._on_transport_failure(session, error),
            )
            state = _SessionState(session, "", process.pid, client, spec.workspace_projection)
            self._states[session.session_id] = state
            self._validate_initialize(client.request("initialize", {"protocolVersion": 1}))
            response = client.request(
                "session/new",
                {"cwd": str(spec.working_directory), "mcpServers": []},
                timeout=20,
            )
            state.external_session_id = _session_id(response)
        except Exception:
            if state is not None:
                self._states.pop(session.session_id, None)
                self._close_state(state)
            elif process is not None:
                self._revoke_model_authority(session)
                self._on_session_closed(session)
                try:
                    self._supervisor.stop(process.pid, timeout=1)
                finally:
                    self._cleanup_spec_projection(spec)
            else:
                self._revoke_model_authority(session)
                self._on_session_closed(session)
                self._cleanup_spec_projection(spec)
            raise
        return session

    def send(self, session: RuntimeSession, message: dict) -> None:
        if not isinstance(message, dict) or not isinstance(message.get("text"), str):
            raise ValueError("message requires text")
        state = self._state_for(session)
        state.prompt_complete.clear()
        Thread(target=self._prompt, args=(state, message["text"]), daemon=True).start()

    def resume(self, session: RuntimeSession) -> None:
        state = self._state_for(session)
        workspace = self._session_workspace(state)
        response = state.client.request("session/load", {
            "cwd": str(workspace), "sessionId": state.external_session_id,
        })
        if response is None:
            raise ValueError("Hermes session cannot be resumed")

    def resolve_approval(self, session: RuntimeSession, approval_id: str, approved: bool) -> None:
        state = self._state_for(session)
        waiter = state.pending_approvals.get(approval_id)
        if waiter is None or not isinstance(approved, bool):
            raise ValueError("unknown Hermes approval")
        state.approvals[approval_id] = approved
        waiter.set()

    def cancel(self, session: RuntimeSession) -> None:
        state = self._state_for(session)
        state.closing = True
        self._notify_terminal(state, RuntimeEventKind.CANCELLED)
        self._wake_approval_waiters(state)
        try:
            if state.client is not None:
                state.client.request(
                    "session/cancel", {"sessionId": state.external_session_id}, timeout=0.25,
                )
        except ValueError:
            pass
        finally:
            self._close_state(state)
            self._states.pop(session.session_id, None)

    def close(self, session: RuntimeSession) -> None:
        state = self._state_for(session)
        state.closing = True
        self._wake_approval_waiters(state)
        try:
            self._close_state(state)
        finally:
            self._states.pop(session.session_id, None)

    def runtime_pid(self, session: RuntimeSession) -> int:
        return self._state_for(session).pid

    def external_session_id(self, session: RuntimeSession) -> str:
        return self._state_for(session).external_session_id

    def drain_events(self, session: RuntimeSession, timeout: float = 1) -> list[RuntimeEvent]:
        state = self._state_for(session)
        state.prompt_complete.wait(timeout)
        if state.error is not None:
            raise state.error
        if not state.prompt_complete.is_set() and not state.events:
            raise ValueError("ACP prompt did not produce an event")
        result, state.events = state.events, []
        return result

    def _spec_for(
        self, session: RuntimeSession, executable: Path, grant: RuntimeProxyGrant | None,
        context_window: int | None,
    ) -> ManagedProcessSpec:
        session_root = self._root / "sessions" / session.session_id
        projection = WorkspaceProjection.create(self._workspace, session_root)
        self._write_isolated_config(projection.hermes_home, grant, context_window)
        return ManagedProcessSpec(
            runtime_id="hermes",
            implementation_version=self._manifest.implementation_version,
            args=[str(executable), *self._executable_args],
            managed_runtime_root=self._root,
            session_root=session_root,
            working_directory=projection.workspace_root,
            environment=grant.environment if grant is not None else {},
            workspace_projection=projection,
        )

    def _model_grant(self, session: RuntimeSession) -> RuntimeProxyGrant | None:
        if self._model_grant_factory is None:
            return None
        grant = self._model_grant_factory(session)
        if not isinstance(grant, RuntimeProxyGrant):
            raise ValueError("model_grant_factory must return RuntimeProxyGrant")
        return grant

    @staticmethod
    def _write_isolated_config(
        hermes_home: Path, grant: RuntimeProxyGrant | None = None, context_window: int | None = None,
    ) -> None:
        hermes_home.mkdir(parents=True, exist_ok=True)
        lines = [
            "memory:",
            "  provider: ''",
            "plugins:",
            "  enabled: []",
        ]
        if context_window is not None:
            lines.extend([
                "model:",
                "  default: bolt-managed",
                "  provider: bolt-managed",
                f"  context_length: {context_window}",
            ])
        elif grant is not None:
            lines.extend([
                "model:",
                "  default: bolt-managed",
                "  provider: custom:bolt",
                f"  context_length: {grant.context_window}",
                "providers:",
                "  bolt:",
                f"    api: {grant.proxy_url}",
                "    transport: chat_completions",
                "    default_model: bolt-managed",
                "    extra_headers:",
                "      X-Bolt-Runtime-Token: ${BOLT_RUNTIME_TOKEN}",
                "      Authorization: ''",
            ])
        (hermes_home / "config.yaml").write_text(
            "\n".join(lines) + "\n", encoding="utf-8",
        )

    def _prompt(self, state: _SessionState, text: str) -> None:
        try:
            response = state.client.request("session/prompt", {
                "sessionId": state.external_session_id,
                "prompt": [{"type": "text", "text": text}],
            }, timeout=125)
            self._record_prompt_response(state, response)
        except Exception as error:
            state.error = error
        finally:
            state.prompt_complete.set()

    def _record_prompt_response(self, state: _SessionState, response: object) -> None:
        usage = prompt_usage_payload(response)
        if usage is not None:
            self._append(state, RuntimeEventKind.USAGE_UPDATE, usage)
        if not isinstance(response, dict):
            raise ValueError("unsupported ACP prompt response")
        if response.get("stopReason") == "cancelled":
            self._notify_terminal(state, RuntimeEventKind.CANCELLED)
            return
        if response.get("stopReason") != "end_turn":
            raise ValueError("unsupported ACP prompt response")
        self._append(state, RuntimeEventKind.COMPLETED, {"summary": "Hermes prompt completed"})
        self._notify_terminal(state, RuntimeEventKind.COMPLETED)

    def _on_message(self, message: dict[str, Any]) -> None:
        if message.get("method") != "session/update":
            return
        params = message.get("params")
        if not isinstance(params, dict):
            return
        state = self._state_by_external_id(params.get("sessionId"))
        if state is None:
            return
        try:
            update = params.get("update")
            if (
                isinstance(update, dict)
                and update.get("sessionUpdate") == "available_commands_update"
            ):
                return
            kind, payload = map_acp_update(update)
            self._append(state, kind, payload)
        except Exception as error:
            state.error = error

    def _on_request(self, client: AcpStdioClient, message: dict[str, Any]) -> None:
        if self._model_bridge is not None and self._model_bridge.handle(
            client, message, lambda external_id: self._session_for_external_id(external_id),
        ):
            return
        parsed = self._parse_permission_request(message)
        if parsed is None:
            self._deny_request(client, message)
            return
        state, tool, approval_id = parsed
        self._wait_for_permission(client, message, state, tool, approval_id)

    def _parse_permission_request(
        self, message: dict[str, Any]
    ) -> tuple[_SessionState, dict[str, Any], str] | None:
        if message.get("method") != "session/request_permission":
            return None
        params = message.get("params")
        if not isinstance(params, dict):
            return None
        state = self._state_by_external_id(params.get("sessionId"))
        tool, options = params.get("toolCall"), params.get("options")
        if state is None or not isinstance(tool, dict):
            return None
        approval_id = tool.get("toolCallId")
        if not isinstance(approval_id, str) or not isinstance(options, list):
            state.error = ValueError("unsupported ACP permission request")
            return None
        if not any(option.get("optionId") == "allow_once" for option in options if isinstance(option, dict)):
            state.error = ValueError("unsupported ACP permission options")
            return None
        return state, tool, approval_id

    def _wait_for_permission(
        self, client: AcpStdioClient, message: dict[str, Any], state: _SessionState,
        tool: dict[str, Any], approval_id: str,
    ) -> None:
        waiter = Event()
        state.pending_approvals[approval_id] = waiter
        self._append(state, RuntimeEventKind.APPROVAL_REQUESTED, {
            "approval_id": approval_id, "tool_id": approval_id,
            "title": tool.get("title", "Hermes permission request"),
        })
        if not waiter.wait(60):
            state.pending_approvals.pop(approval_id, None)
            self._deny_request(client, message)
            return
        if state.closing or state.error is not None:
            state.pending_approvals.pop(approval_id, None)
            state.approvals.pop(approval_id, None)
            return
        approved = state.approvals.pop(approval_id, False)
        state.pending_approvals.pop(approval_id, None)
        self._append(state, RuntimeEventKind.APPROVAL_RESOLVED, {
            "approval_id": approval_id, "approved": approved,
        })
        outcome = {"outcome": "selected", "optionId": "allow_once"} if approved else {"outcome": "cancelled"}
        client.respond(message.get("id"), {"outcome": outcome})

    @staticmethod
    def _deny_request(client: AcpStdioClient, message: dict[str, Any]) -> None:
        client.respond(message.get("id"), {"outcome": {"outcome": "cancelled"}})

    def _on_transport_failure(self, session: RuntimeSession, error: Exception) -> None:
        try:
            state = self._state_for(session)
        except ValueError:
            return
        if state.closing:
            return
        state.error = error
        state.prompt_complete.set()
        self._wake_approval_waiters(state)
        self._notify_terminal(state, RuntimeEventKind.FAILED)
        self._close_state(state)

    def _notify_terminal(self, state: _SessionState, kind: RuntimeEventKind) -> None:
        if state.terminal_notified:
            return
        state.terminal_notified = True
        self._on_terminal(state.session, kind)

    @staticmethod
    def _wake_approval_waiters(state: _SessionState) -> None:
        for waiter in tuple(state.pending_approvals.values()):
            waiter.set()

    def _close_state(self, state: _SessionState) -> None:
        if state.closure_notified:
            return
        state.closure_notified = True
        self._revoke_model_authority(state.session)
        self._on_session_closed(state.session)
        try:
            self._supervisor.stop(state.pid, timeout=1)
        finally:
            if state.projection is not None and state.projection.session_root.exists():
                state.projection.cleanup()

    @staticmethod
    def _cleanup_spec_projection(spec: ManagedProcessSpec | None) -> None:
        projection = spec.workspace_projection if spec is not None else None
        if projection is not None and projection.session_root.exists():
            projection.cleanup()

    def _append(self, state: _SessionState, kind: RuntimeEventKind, payload: dict) -> None:
        event = RuntimeEvent(
            event_id=f"evt_{uuid4().hex}", task_id=state.session.task_id,
            runtime_id="hermes", session_id=state.session.session_id,
            sequence=state.next_sequence, timestamp=datetime.now(UTC), kind=kind, payload=payload,
        )
        state.next_sequence += 1
        state.events.append(event)

    def _state_for(self, session: RuntimeSession) -> _SessionState:
        if not isinstance(session, RuntimeSession) or session.runtime_id != "hermes":
            raise ValueError("session runtime_id does not match Hermes")
        try:
            return self._states[session.session_id]
        except KeyError as error:
            raise ValueError("unknown Hermes session") from error

    def _state_by_external_id(self, session_id: object) -> _SessionState | None:
        return next((state for state in self._states.values() if state.external_session_id == session_id), None)

    def _session_for_external_id(self, session_id: object) -> RuntimeSession | None:
        state = self._state_by_external_id(session_id)
        return state.session if state is not None else None

    def _revoke_model_authority(self, session: RuntimeSession) -> None:
        if self._model_bridge is not None:
            self._model_bridge.revoke(session)

    @staticmethod
    def _session_workspace(state: _SessionState) -> Path:
        if state.projection is None:
            raise ValueError("workspace_projection_required")
        return state.projection.workspace_root

    def _validate_initialize(self, response: object) -> None:
        if not isinstance(response, dict):
            raise ValueError("invalid ACP initialize response")
        agent = response.get("agentInfo")
        capabilities = response.get("agentCapabilities")
        if response.get("protocolVersion") != 1 or not isinstance(agent, dict):
            raise ValueError("invalid ACP initialize response")
        if agent.get("name") != "hermes-agent" or agent.get("version") != self._manifest.implementation_version:
            raise ValueError("invalid ACP initialize response")
        if not isinstance(capabilities, dict) or capabilities.get("loadSession") is not True:
            raise ValueError("invalid ACP initialize response")


def _session_id(response: object) -> str:
    if not isinstance(response, dict) or not isinstance(response.get("sessionId"), str):
        raise ValueError("invalid ACP new session response")
    return response["sessionId"]
