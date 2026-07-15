from datetime import UTC, datetime

import pytest

from bolt_core.model_proxy import RuntimeModelProxy
from bolt_core.model_proxy_server import ModelProxyServer
from bolt_core.runtime.contracts import RuntimeSession
from bolt_core.runtime.model_access import (
    RuntimeModelAccessBroker, RuntimeModelPolicy, RuntimeProxyGrant,
)
from bolt_core.runtime_token_store import RuntimeTokenClaims, RuntimeTokenError, RuntimeTokenStore


class Gateway:
    def complete(self, _profile_id, _payload):
        return {"choices": []}


def _broker():
    now = lambda: datetime(2026, 7, 13, 1, tzinfo=UTC)
    tokens = RuntimeTokenStore(now)
    proxy = RuntimeModelProxy(tokens, Gateway())
    server = ModelProxyServer(proxy)
    return RuntimeModelAccessBroker(tokens, server)


def _policy():
    return RuntimeModelPolicy(
        model_profile_id="profile_12345678",
        allowed_paths=("/v1/chat/completions",),
        budget=3,
        expires_at=datetime(2026, 7, 13, 1, 5, tzinfo=UTC),
        generation=4,
        context_window=128_000,
    )


def test_broker_issues_only_fixed_proxy_environment_for_runtime_session():
    broker = _broker()
    broker.start()
    session = RuntimeSession("session_12345678", "hermes", "task_12345678")

    grant = broker.issue(session, _policy())

    assert grant.environment == {
        "BOLT_MODEL_PROXY_URL": f"http://127.0.0.1:{broker.port}/v1",
        "BOLT_RUNTIME_TOKEN": grant.token,
        "NO_PROXY": "127.0.0.1,localhost",
    }
    authorization = broker.tokens.authorize_proxy(
        grant.token, path="/v1/chat/completions", request_id="request_12345678",
    )
    assert authorization.claims.model_profile_id == "profile_12345678"
    broker.stop()


def test_broker_revokes_all_session_tokens_without_affecting_another_session():
    broker = _broker()
    broker.start()
    first = RuntimeSession("session_12345678", "hermes", "task_12345678")
    other = RuntimeSession("session_87654321", "hermes", "task_87654321")
    first_grant = broker.issue(first, _policy())
    other_grant = broker.issue(other, _policy())

    broker.revoke_session(first)

    with pytest.raises(RuntimeTokenError, match="invalid"):
        broker.tokens.authorize_proxy(
            first_grant.token, path="/v1/chat/completions", request_id="request_12345678",
        )
    assert broker.tokens.authorize_proxy(
        other_grant.token, path="/v1/chat/completions", request_id="request_87654321",
    ).remaining_budget == 2
    broker.stop()


def test_proxy_grant_does_not_accept_caller_controlled_environment():
    with pytest.raises(ValueError, match="proxy URL"):
        RuntimeProxyGrant("runtime-token", "https://attacker.invalid/v1", 128_000)


def test_broker_rejects_untrusted_policy_object():
    broker = _broker()
    session = RuntimeSession("session_12345678", "hermes", "task_12345678")

    with pytest.raises(ValueError, match="RuntimeModelPolicy"):
        broker.issue(session, {"model_profile_id": "attacker"})
