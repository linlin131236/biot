from concurrent.futures import ThreadPoolExecutor
import json
from datetime import UTC, datetime
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from bolt_core.model_proxy import ModelProxyServer, RuntimeModelProxy
from bolt_core.runtime_token_store import RuntimeTokenClaims, RuntimeTokenStore


class Clock:
    def now(self):
        return datetime(2026, 7, 12, 12, 0, tzinfo=UTC)


class Gateway:
    def complete(self, _profile_id, _payload):
        return {"id": "response_123", "choices": [{"message": {"content": "safe"}}]}


def _server():
    store = RuntimeTokenStore(Clock().now)
    token = store.issue(RuntimeTokenClaims(
        runtime_id="hermes", runtime_session_id="session_12345678", model_profile_id="profile_12345678",
        allowed_paths=("/v1/chat/completions",), budget=100,
        expires_at=datetime(2026, 7, 12, 12, 5, tzinfo=UTC), generation=1,
    ))
    return ModelProxyServer(RuntimeModelProxy(store, Gateway())), token


def _request(server, token, body=None):
    return Request(
        f"http://{server.host}:{server.port}/v1/chat/completions",
        data=json.dumps(body or {"messages": [{"role": "user", "content": "hello"}]}).encode(),
        method="POST",
        headers={"x-bolt-runtime-token": token, "content-type": "application/json"},
    )


def test_model_proxy_server_binds_only_loopback_random_port_and_handles_bearer_request():
    server, token = _server()
    server.start()

    with urlopen(_request(server, token)) as response:
        payload = json.loads(response.read())

    server.stop()
    assert server.host == "127.0.0.1"
    assert server.port > 0
    assert payload["choices"][0]["message"]["content"] == "safe"


def test_model_proxy_server_rejects_token_or_binding_fields_in_runtime_body():
    server, token = _server()
    server.start()
    request = _request(server, token, {"token": token, "cost": 0})

    try:
        urlopen(request)
    except HTTPError as error:
        assert error.code == 403
        assert token not in error.read().decode()
    else:
        raise AssertionError("body must not control model authorization")
    finally:
        server.stop()


def test_model_proxy_server_rejects_authorization_header():
    server, token = _server()
    server.start()
    request = _request(server, token)
    request.add_header("authorization", "Bearer provider-secret")

    with pytest.raises(HTTPError) as error:
        urlopen(request)

    server.stop()
    assert error.value.code == 403


def test_model_proxy_server_rejects_oversized_body_before_gateway_invocation():
    server, token = _server()
    server.start()
    request = _request(server, token, {"messages": [{"content": "x" * (64 * 1024)}]})

    try:
        urlopen(request)
    except HTTPError as error:
        assert error.code == 400
    else:
        raise AssertionError("oversized request must be rejected")
    finally:
        server.stop()


def test_model_proxy_server_rejects_replayed_request_under_concurrent_requests():
    server, token = _server()
    server.start()

    def send() -> int:
        try:
            return urlopen(_request(server, token)).status
        except HTTPError as error:
            return error.code

    with ThreadPoolExecutor(max_workers=2) as executor:
        statuses = list(executor.map(lambda _index: send(), range(2)))
    server.stop()

    assert sorted(statuses) == [200, 200]
