from datetime import UTC, datetime, timedelta

from bolt_core.runtime.contracts import RuntimeSession
from bolt_core.runtime.hermes_model_bridge import HermesModelBridge
from bolt_core.runtime.model_access import RuntimeModelPolicy
from bolt_core.runtime.model_rpc import RuntimeModelRpcError


class Client:
    def __init__(self) -> None:
        self.responses = []
        self.errors = []

    def respond(self, request_id, result) -> None:
        self.responses.append((request_id, result))

    def respond_error(self, request_id, code, message) -> None:
        self.errors.append((request_id, code, message))


class Rpc:
    def __init__(self) -> None:
        self.registered = []
        self.requests = []
        self.revoked = []
        self.error = None

    def register(self, session, policy) -> None:
        self.registered.append((session, policy))

    def complete(self, session, payload):
        self.requests.append((session, payload))
        if self.error is not None:
            raise self.error
        return {"choices": [{"message": {"content": "safe"}}]}

    def revoke(self, session) -> None:
        self.revoked.append(session)


def _session():
    return RuntimeSession("session_12345678", "hermes", "task_12345678")


def _policy():
    return RuntimeModelPolicy(
        "profile_12345678", ("/v1/chat/completions",), 3,
        datetime.now(UTC) + timedelta(minutes=5), 4, 128_000,
    )


def _request(**changes):
    values = {
        "id": 7,
        "method": "_bolt/model.complete",
        "params": {
            "sessionId": "external_12345678",
            "payload": {"messages": [{"role": "user", "content": "hello"}]},
        },
    }
    return {**values, **changes}


def test_bridge_accepts_only_the_standard_acp_extension_wire_method():
    rpc = Rpc()
    session = _session()
    bridge = HermesModelBridge(rpc, lambda value: _policy())
    client = Client()
    bridge.register(session)
    request = _request(method="_bolt/model.complete")

    assert bridge.handle(client, request, lambda external_id: session) is True
    assert rpc.requests == [(session, request["params"]["payload"])]
    assert client.responses == [(7, {"choices": [{"message": {"content": "safe"}}]})]

    legacy_client = Client()
    assert bridge.handle(
        legacy_client,
        _request(method="bolt/model.complete"),
        lambda _external_id: session,
    ) is False
    assert legacy_client.responses == []
    assert legacy_client.errors == []


def test_bridge_registers_core_policy_and_serves_only_external_session_payload():
    rpc = Rpc()
    session = _session()
    bridge = HermesModelBridge(rpc, lambda value: _policy())
    client = Client()
    bridge.register(session)

    handled = bridge.handle(client, _request(), lambda external_id: session if external_id == "external_12345678" else None)

    assert handled is True
    assert rpc.registered == [(session, _policy())]
    assert rpc.requests == [(session, _request()["params"]["payload"])]
    assert client.responses == [(7, {"choices": [{"message": {"content": "safe"}}]})]
    assert client.errors == []


def test_bridge_rejects_model_identity_or_credential_fields_before_core_call():
    rpc = Rpc()
    session = _session()
    bridge = HermesModelBridge(rpc, lambda value: _policy())
    bridge.register(session)
    client = Client()
    request = _request()
    request["params"] = request["params"] | {"model_profile_id": "attacker"}

    assert bridge.handle(client, request, lambda _external_id: session) is True

    assert rpc.requests == []
    assert client.responses == []
    assert client.errors == [(7, -32602, "Invalid params")]


def test_bridge_rejects_unknown_external_session_before_core_call():
    rpc = Rpc()
    bridge = HermesModelBridge(rpc, lambda value: _policy())
    client = Client()

    assert bridge.handle(client, _request(), lambda _external_id: None) is True

    assert rpc.requests == []
    assert client.errors == [(7, -32602, "Invalid params")]


def test_bridge_maps_core_authority_failure_to_a_generic_rpc_error():
    rpc = Rpc()
    rpc.error = RuntimeModelRpcError("runtime_model_authority_invalid: secret-canary")
    session = _session()
    bridge = HermesModelBridge(rpc, lambda value: _policy())
    bridge.register(session)
    client = Client()

    assert bridge.handle(client, _request(), lambda _external_id: session) is True

    assert client.responses == []
    assert client.errors == [(7, -32000, "Model request rejected")]


def test_bridge_revoke_delegates_to_core_authority_once_registered():
    rpc = Rpc()
    session = _session()
    bridge = HermesModelBridge(rpc, lambda value: _policy())
    bridge.register(session)

    bridge.revoke(session)

    assert rpc.revoked == [session]
