from dataclasses import replace
from datetime import UTC, datetime, timedelta
from threading import Event, Thread

import pytest

from bolt_core.model_proxy import RuntimeModelProxy
from bolt_core.runtime.contracts import RuntimeSession
from bolt_core.runtime.model_access import RuntimeModelPolicy
from bolt_core.runtime.model_rpc import RuntimeModelRpc, RuntimeModelRpcError
from bolt_core.runtime_token_store import RuntimeTokenStore


class Clock:
    def __init__(self) -> None:
        self.value = datetime(2026, 7, 14, 12, tzinfo=UTC)

    def now(self) -> datetime:
        return self.value


class Gateway:
    def __init__(self) -> None:
        self.requests = []

    def complete(self, profile_id, request):
        self.requests.append((profile_id, request))
        return {"choices": [{"message": {"content": "safe"}}]}


def _session(suffix="12345678"):
    return RuntimeSession(f"session_{suffix}", "hermes", f"task_{suffix}")


def _policy(clock, *, budget=2, generation=4):
    return RuntimeModelPolicy(
        model_profile_id="profile_12345678",
        allowed_paths=("/v1/chat/completions",),
        budget=budget,
        expires_at=clock.now() + timedelta(minutes=5),
        generation=generation,
        context_window=128_000,
    )


def _rpc(clock, gateway=None):
    gateway = gateway or Gateway()
    proxy = RuntimeModelProxy(RuntimeTokenStore(clock.now), gateway)
    return RuntimeModelRpc(proxy, now=clock.now), gateway


def _payload():
    return {"messages": [{"role": "user", "content": "hello"}]}


def test_core_model_rpc_derives_profile_and_generation_only_from_registered_authority():
    clock = Clock()
    rpc, gateway = _rpc(clock)
    session = _session()
    rpc.register(session, _policy(clock))

    response = rpc.complete(session, _payload())

    assert response == {"choices": [{"message": {"content": "safe"}}]}
    assert gateway.requests == [("profile_12345678", {
        "path": "/v1/chat/completions", "payload": _payload(), "generation": 4,
    })]
    assert "profile_12345678" not in str(_payload())


@pytest.mark.parametrize("change", [
    {"allowed_paths": ("/v1/models",)},
    {"budget": -1},
    {"generation": -1},
])
def test_core_model_rpc_rejects_policy_outside_its_fixed_model_operation(change):
    clock = Clock()
    rpc, _gateway = _rpc(clock)

    with pytest.raises(ValueError, match="runtime model authority"):
        rpc.register(_session(), replace(_policy(clock), **change))


@pytest.mark.parametrize("field", ["api_key", "authorization", "base_url", "credential_id", "token"])
def test_core_model_rpc_rejects_runtime_controlled_fields_before_provider_call(field):
    clock = Clock()
    rpc, gateway = _rpc(clock)
    session = _session()
    rpc.register(session, _policy(clock))

    with pytest.raises(ValueError, match="runtime model payload"):
        rpc.complete(session, _payload() | {field: "attacker"})

    assert gateway.requests == []


def test_core_model_rpc_rejects_invalid_payload_without_spending_budget():
    clock = Clock()
    rpc, gateway = _rpc(clock)
    session = _session()
    rpc.register(session, _policy(clock, budget=1))

    with pytest.raises(ValueError, match="runtime model payload"):
        rpc.complete(session, _payload() | {"token": "attacker"})

    assert rpc.complete(session, _payload())["choices"][0]["message"]["content"] == "safe"
    assert len(gateway.requests) == 1


def test_core_model_rpc_rejects_unknown_or_revoked_session_before_provider_call():
    clock = Clock()
    rpc, gateway = _rpc(clock)
    session = _session()
    rpc.register(session, _policy(clock))
    rpc.revoke(session)

    with pytest.raises(RuntimeModelRpcError, match="authority_invalid"):
        rpc.complete(session, _payload())
    with pytest.raises(RuntimeModelRpcError, match="authority_invalid"):
        rpc.complete(_session("87654321"), _payload())

    assert gateway.requests == []


def test_core_model_rpc_rejects_expired_authority_before_provider_call():
    clock = Clock()
    rpc, gateway = _rpc(clock)
    session = _session()
    rpc.register(session, _policy(clock))
    clock.value += timedelta(minutes=5)

    with pytest.raises(RuntimeModelRpcError, match="authority_expired"):
        rpc.complete(session, _payload())

    assert gateway.requests == []


def test_core_model_rpc_spends_budget_atomically_under_concurrent_requests():
    clock = Clock()
    started, release = Event(), Event()

    class BlockingGateway(Gateway):
        def complete(self, profile_id, request):
            self.requests.append((profile_id, request))
            started.set()
            assert release.wait(timeout=1)
            return {"choices": [{"message": {"content": "safe"}}]}

    rpc, gateway = _rpc(clock, BlockingGateway())
    session = _session()
    rpc.register(session, _policy(clock, budget=1))
    completed = []

    thread = Thread(target=lambda: completed.append(rpc.complete(session, _payload())))
    thread.start()
    assert started.wait(timeout=1)
    with pytest.raises(RuntimeModelRpcError, match="budget_exhausted"):
        rpc.complete(session, _payload())
    release.set()
    thread.join(timeout=1)

    assert completed == [{"choices": [{"message": {"content": "safe"}}]}]
    assert len(gateway.requests) == 1


def test_core_model_rpc_discards_inflight_response_when_session_is_revoked():
    clock = Clock()
    started, release, revoked = Event(), Event(), Event()

    class BlockingGateway(Gateway):
        def complete(self, profile_id, request):
            self.requests.append((profile_id, request))
            started.set()
            assert release.wait(timeout=1)
            return {"choices": [{"message": {"content": "safe"}}]}

    rpc, gateway = _rpc(clock, BlockingGateway())
    session = _session()
    rpc.register(session, _policy(clock))
    failures = []

    request = Thread(target=lambda: _capture(failures, lambda: rpc.complete(session, _payload())))
    request.start()
    assert started.wait(timeout=1)
    revoker = Thread(target=lambda: (rpc.revoke(session), revoked.set()))
    revoker.start()
    assert revoked.wait(timeout=1)
    release.set()
    request.join(timeout=1)
    revoker.join(timeout=1)

    assert revoked.is_set()
    assert failures == ["runtime_model_authority_invalid"]
    with pytest.raises(RuntimeModelRpcError, match="authority_invalid"):
        rpc.complete(session, _payload())
    assert len(gateway.requests) == 1


def test_core_model_rpc_revokes_authority_when_profile_generation_changes():
    class ChangedGateway(Gateway):
        def complete(self, profile_id, request):
            self.requests.append((profile_id, request))
            raise RuntimeError("model_profile_generation_changed")

    clock = Clock()
    rpc, gateway = _rpc(clock, ChangedGateway())
    session = _session()
    rpc.register(session, _policy(clock))

    with pytest.raises(RuntimeModelRpcError, match="authority_invalid"):
        rpc.complete(session, _payload())
    with pytest.raises(RuntimeModelRpcError, match="authority_invalid"):
        rpc.complete(session, _payload())

    assert len(gateway.requests) == 1


def _capture(errors, operation) -> None:
    try:
        operation()
    except RuntimeModelRpcError as error:
        errors.append(str(error))
