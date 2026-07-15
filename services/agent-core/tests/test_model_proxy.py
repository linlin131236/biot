from datetime import UTC, datetime
from threading import Event, Thread

import pytest

from bolt_core.model_proxy import ModelProxyRequest, RuntimeModelProxy
from bolt_core.runtime_token_store import RuntimeTokenClaims, RuntimeTokenError, RuntimeTokenStore


class Clock:
    def __init__(self):
        self.value = datetime(2026, 7, 12, 12, 0, tzinfo=UTC)

    def now(self):
        return self.value


class RecordingGateway:
    def __init__(self):
        self.requests = []

    def complete(self, profile_id, payload):
        self.requests.append((profile_id, payload))
        return {"id": "response_123", "choices": [{"message": {"content": "safe"}}]}


def _proxy(gateway=None):
    clock = Clock()
    store = RuntimeTokenStore(clock.now)
    token = store.issue(RuntimeTokenClaims(
        runtime_id="hermes",
        runtime_session_id="session_12345678",
        model_profile_id="profile_12345678",
        allowed_paths=("/v1/chat/completions",),
        budget=100,
        expires_at=datetime(2026, 7, 12, 12, 5, tzinfo=UTC),
        generation=1,
    ))
    gateway = gateway or RecordingGateway()
    return RuntimeModelProxy(store, gateway), token, gateway


def _request(token, **changes):
    values = {
        "token": token,
        "request_id": "request_12345678",
        "path": "/v1/chat/completions",
        "payload": {"model": "runtime-cannot-select", "messages": [{"role": "user", "content": "hello"}]},
    }
    return ModelProxyRequest(**{**values, **changes})


def test_model_proxy_derives_profile_from_claims_and_drops_runtime_model():
    proxy, token, gateway = _proxy()

    response = proxy.complete(_request(token))

    assert response["choices"][0]["message"]["content"] == "safe"
    profile_id, forwarded = gateway.requests[0]
    assert profile_id == "profile_12345678"
    assert forwarded == {
        "path": "/v1/chat/completions",
        "payload": {"messages": [{"role": "user", "content": "hello"}]},
        "generation": 1,
    }
    assert "token" not in str(forwarded).lower()


@pytest.mark.parametrize(
    "field", ["base_url", "provider", "api_key", "authorization", "cost", "runtime_session_id", "headers"],
)
def test_model_proxy_rejects_runtime_controlled_upstream_or_binding_fields(field):
    proxy, token, _gateway = _proxy()
    payload = _request(token).payload | {field: "attacker-controlled"}

    with pytest.raises(ValueError, match="runtime model payload"):
        proxy.complete(_request(token, payload=payload))


def test_model_proxy_revokes_generation_when_the_saved_profile_changes():
    class ChangedProfileGateway:
        def __init__(self):
            self.calls = []

        def complete(self, profile_id, request):
            self.calls.append((profile_id, request))
            raise RuntimeError("model_profile_generation_changed")

    gateway = ChangedProfileGateway()
    proxy, token, _gateway = _proxy(gateway)

    with pytest.raises(RuntimeError, match="generation_changed"):
        proxy.complete(_request(token))
    with pytest.raises(RuntimeTokenError, match="invalid"):
        proxy.complete(_request(token, request_id="request_87654321"))

    assert len(gateway.calls) == 1

def test_model_proxy_rejects_explicitly_revoked_token():
    proxy, token, gateway = _proxy()
    proxy.revoke(token)

    with pytest.raises(RuntimeTokenError):
        proxy.complete(_request(token))

    assert gateway.requests == []


def test_model_proxy_rejects_non_object_payload_before_token_spend():
    proxy, token, gateway = _proxy()

    with pytest.raises(ValueError, match="runtime model payload"):
        proxy.complete(_request(token, payload=[]))

    assert gateway.requests == []


def test_model_proxy_rejects_non_allowlisted_request_path_before_gateway_call():
    proxy, token, gateway = _proxy()

    with pytest.raises(RuntimeTokenError, match="path_not_allowed"):
        proxy.complete(_request(token, path="/v1/models"))

    assert gateway.requests == []


def test_model_proxy_discards_in_flight_response_after_session_revocation():
    started, release = Event(), Event()

    class BlockingGateway:
        def complete(self, _profile_id, _payload):
            started.set()
            release.wait(timeout=1)
            return {"choices": []}

    proxy, token, _gateway = _proxy(BlockingGateway())
    failures = []

    def run() -> None:
        try:
            proxy.complete(_request(token))
        except RuntimeTokenError as error:
            failures.append(str(error))

    thread = Thread(target=run)
    thread.start()
    assert started.wait(timeout=1)
    proxy.revoke_session("hermes", "session_12345678")
    release.set()
    thread.join(timeout=1)

    assert failures == ["runtime_token_invalid"]
