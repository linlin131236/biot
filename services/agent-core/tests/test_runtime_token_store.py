from dataclasses import replace
from datetime import UTC, datetime
from threading import Barrier, Thread

import pytest

from bolt_core.runtime_token_store import RuntimeTokenClaims, RuntimeTokenError, RuntimeTokenStore


class Clock:
    def __init__(self, value: datetime) -> None:
        self.value = value

    def now(self) -> datetime:
        return self.value


def _claims(*, generation: int = 1, budget: int = 100) -> RuntimeTokenClaims:
    return RuntimeTokenClaims(
        runtime_id="bolt-native",
        runtime_session_id="session_12345678",
        model_profile_id="profile_12345678",
        allowed_paths=("/workspace",),
        budget=budget,
        expires_at=datetime(2026, 7, 12, 12, 5, tzinfo=UTC),
        generation=generation,
    )


def test_issued_token_is_opaque_unique_and_authorizes_its_bound_operation():
    clock = Clock(datetime(2026, 7, 12, 12, 0, tzinfo=UTC))
    store = RuntimeTokenStore(clock.now)
    claims = _claims()

    first = store.issue(claims)
    second = store.issue(claims)
    authorization = store.authorize(
        first,
        runtime_id="bolt-native",
        runtime_session_id="session_12345678",
        model_profile_id="profile_12345678",
        generation=1,
        path="/workspace/src/main.py",
        cost=10,
        request_id="request_12345678",
    )

    assert first != second
    assert "session_12345678" not in first
    assert authorization.claims == claims
    assert authorization.remaining_budget == 90


def test_store_uses_utc_clock_when_callers_do_not_inject_one():
    assert isinstance(RuntimeTokenStore(), RuntimeTokenStore)


def test_issue_retries_an_unlikely_random_token_collision(monkeypatch):
    values = iter(["opaque-token", "opaque-token", "next-opaque-token"])
    monkeypatch.setattr(
        "bolt_core.runtime_token_store.secrets.token_urlsafe", lambda _size: next(values)
    )
    store = RuntimeTokenStore(Clock(datetime(2026, 7, 12, 12, 0, tzinfo=UTC)).now)

    first = store.issue(_claims())
    second = store.issue(_claims())

    assert (first, second) == ("opaque-token", "next-opaque-token")


def test_process_restart_forgets_pre_crash_tokens():
    clock = Clock(datetime(2026, 7, 12, 12, 0, tzinfo=UTC))
    token = RuntimeTokenStore(clock.now).issue(_claims())
    restarted = RuntimeTokenStore(clock.now)

    with pytest.raises(RuntimeTokenError, match="runtime_token_invalid"):
        restarted.authorize(
            token,
            runtime_id="bolt-native",
            runtime_session_id="session_12345678",
            model_profile_id="profile_12345678",
            generation=1,
            path="/workspace/main.py",
            cost=1,
            request_id="request_12345678",
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("runtime_id", "other-runtime"),
        ("runtime_session_id", "session_other"),
        ("model_profile_id", "profile_other"),
        ("generation", 2),
    ],
)
def test_token_rejects_cross_runtime_or_binding_mixup_without_spending_budget(field, value):
    clock = Clock(datetime(2026, 7, 12, 12, 0, tzinfo=UTC))
    store = RuntimeTokenStore(clock.now)
    token = store.issue(_claims())
    operation = {
        "runtime_id": "bolt-native",
        "runtime_session_id": "session_12345678",
        "model_profile_id": "profile_12345678",
        "generation": 1,
        "path": "/workspace/src/main.py",
        "cost": 10,
    }
    mixed_operation = {**operation, field: value}

    with pytest.raises(RuntimeTokenError, match="binding_mismatch"):
        store.authorize(token, request_id="request_12345678", **mixed_operation)

    authorization = store.authorize(token, request_id="request_87654321", **operation)
    assert authorization.remaining_budget == 90


def test_token_rejects_replayed_request_id_without_spending_budget_twice():
    clock = Clock(datetime(2026, 7, 12, 12, 0, tzinfo=UTC))
    store = RuntimeTokenStore(clock.now)
    token = store.issue(_claims())
    operation = {
        "runtime_id": "bolt-native",
        "runtime_session_id": "session_12345678",
        "model_profile_id": "profile_12345678",
        "generation": 1,
        "path": "/workspace/main.py",
        "cost": 10,
        "request_id": "request_12345678",
    }

    first = store.authorize(token, **operation)

    with pytest.raises(RuntimeTokenError, match="replayed"):
        store.authorize(token, **operation)

    second = store.authorize(token, request_id="request_87654321", **{
        key: value for key, value in operation.items() if key != "request_id"
    })
    assert first.remaining_budget == 90
    assert second.remaining_budget == 80


def test_token_rejects_cost_over_its_remaining_budget_without_spending_budget():
    clock = Clock(datetime(2026, 7, 12, 12, 0, tzinfo=UTC))
    store = RuntimeTokenStore(clock.now)
    token = store.issue(_claims(budget=10))
    operation = {
        "runtime_id": "bolt-native",
        "runtime_session_id": "session_12345678",
        "model_profile_id": "profile_12345678",
        "generation": 1,
        "path": "/workspace/main.py",
    }

    with pytest.raises(RuntimeTokenError, match="budget_exhausted"):
        store.authorize(token, cost=11, request_id="request_12345678", **operation)

    authorization = store.authorize(token, cost=10, request_id="request_87654321", **operation)
    assert authorization.remaining_budget == 0


def test_token_rejects_authorization_at_or_after_its_expiry():
    clock = Clock(datetime(2026, 7, 12, 12, 0, tzinfo=UTC))
    store = RuntimeTokenStore(clock.now)
    token = store.issue(_claims())
    clock.value = datetime(2026, 7, 12, 12, 5, tzinfo=UTC)

    with pytest.raises(RuntimeTokenError, match="expired"):
        store.authorize(
            token,
            runtime_id="bolt-native",
            runtime_session_id="session_12345678",
            model_profile_id="profile_12345678",
            generation=1,
            path="/workspace/main.py",
            cost=10,
            request_id="request_12345678",
        )


def test_revoke_invalidates_all_tokens_for_one_runtime_session_only():
    clock = Clock(datetime(2026, 7, 12, 12, 0, tzinfo=UTC))
    store = RuntimeTokenStore(clock.now)
    first = store.issue(_claims())
    second = store.issue(_claims())
    other_claims = RuntimeTokenClaims(
        runtime_id="bolt-native",
        runtime_session_id="session_87654321",
        model_profile_id="profile_12345678",
        allowed_paths=("/workspace",),
        budget=100,
        expires_at=datetime(2026, 7, 12, 12, 5, tzinfo=UTC),
        generation=1,
    )
    other = store.issue(other_claims)
    operation = {
        "runtime_id": "bolt-native",
        "model_profile_id": "profile_12345678",
        "generation": 1,
        "path": "/workspace/main.py",
        "cost": 1,
    }

    store.revoke_session("bolt-native", "session_12345678")

    for token in (first, second):
        with pytest.raises(RuntimeTokenError, match="invalid"):
            store.authorize(token, runtime_session_id="session_12345678", request_id=token, **operation)
    assert store.authorize(
        other,
        runtime_session_id="session_87654321",
        request_id="request_12345678",
        **operation,
    ).remaining_budget == 99
    with pytest.raises(RuntimeTokenError, match="session_revoked"):
        store.issue(_claims())


def test_revoke_invalidates_only_the_named_token():
    clock = Clock(datetime(2026, 7, 12, 12, 0, tzinfo=UTC))
    store = RuntimeTokenStore(clock.now)
    revoked = store.issue(_claims())
    active = store.issue(_claims())
    operation = {
        "runtime_id": "bolt-native",
        "runtime_session_id": "session_12345678",
        "model_profile_id": "profile_12345678",
        "generation": 1,
        "path": "/workspace/main.py",
        "cost": 1,
    }

    store.revoke(revoked)

    with pytest.raises(RuntimeTokenError, match="invalid"):
        store.authorize(revoked, request_id="request_12345678", **operation)
    assert store.authorize(active, request_id="request_87654321", **operation).remaining_budget == 99


def test_unknown_token_is_rejected_with_the_same_runtime_token_error():
    store = RuntimeTokenStore(Clock(datetime(2026, 7, 12, 12, 0, tzinfo=UTC)).now)

    with pytest.raises(RuntimeTokenError, match="runtime_token_invalid"):
        store.authorize(
            "unknown-token",
            runtime_id="bolt-native",
            runtime_session_id="session_12345678",
            model_profile_id="profile_12345678",
            generation=1,
            path="/workspace/main.py",
            cost=1,
            request_id="request_12345678",
        )


@pytest.mark.parametrize("token", [None, []])
def test_authorize_rejects_non_string_tokens_with_runtime_token_error(token):
    store = RuntimeTokenStore(Clock(datetime(2026, 7, 12, 12, 0, tzinfo=UTC)).now)

    with pytest.raises(RuntimeTokenError, match="runtime_token_invalid"):
        store.authorize(
            token,
            runtime_id="bolt-native",
            runtime_session_id="session_12345678",
            model_profile_id="profile_12345678",
            generation=1,
            path="/workspace/main.py",
            cost=1,
            request_id="request_12345678",
        )


@pytest.mark.parametrize("token", ["unknown-token", []])
def test_revoke_rejects_unknown_or_invalid_token_with_runtime_token_error(token):
    store = RuntimeTokenStore(Clock(datetime(2026, 7, 12, 12, 0, tzinfo=UTC)).now)

    with pytest.raises(RuntimeTokenError, match="runtime_token_invalid"):
        store.revoke(token)


def test_revoke_generation_invalidates_only_its_generation():
    clock = Clock(datetime(2026, 7, 12, 12, 0, tzinfo=UTC))
    store = RuntimeTokenStore(clock.now)
    revoked = store.issue(_claims(generation=1))
    active = store.issue(_claims(generation=2))
    operation = {
        "runtime_id": "bolt-native",
        "runtime_session_id": "session_12345678",
        "model_profile_id": "profile_12345678",
        "path": "/workspace/main.py",
        "cost": 1,
    }

    store.revoke_generation("bolt-native", "session_12345678", "profile_12345678", 1)

    with pytest.raises(RuntimeTokenError, match="invalid"):
        store.authorize(revoked, generation=1, request_id="request_12345678", **operation)
    assert store.authorize(active, generation=2, request_id="request_87654321", **operation).remaining_budget == 99
    with pytest.raises(RuntimeTokenError, match="generation_revoked"):
        store.issue(_claims(generation=1))


def test_revoke_generation_does_not_invalidate_other_runtime_sessions():
    clock = Clock(datetime(2026, 7, 12, 12, 0, tzinfo=UTC))
    store = RuntimeTokenStore(clock.now)
    first = store.issue(_claims(generation=1))
    other_claims = replace(_claims(generation=1), runtime_session_id="session_87654321")
    other = store.issue(other_claims)
    operation = {
        "runtime_id": "bolt-native",
        "model_profile_id": "profile_12345678",
        "generation": 1,
        "path": "/workspace/main.py",
        "cost": 1,
    }

    store.revoke_generation("bolt-native", "session_12345678", "profile_12345678", 1)

    with pytest.raises(RuntimeTokenError, match="invalid"):
        store.authorize(first, runtime_session_id="session_12345678", request_id="request_12345678", **operation)
    assert store.authorize(
        other, runtime_session_id="session_87654321", request_id="request_87654321", **operation
    ).remaining_budget == 99


def test_revoke_generation_does_not_invalidate_other_profile_in_same_session():
    clock = Clock(datetime(2026, 7, 12, 12, 0, tzinfo=UTC))
    store = RuntimeTokenStore(clock.now)
    first = store.issue(_claims(generation=1))
    other_claims = replace(_claims(generation=1), model_profile_id="profile_87654321")
    other = store.issue(other_claims)

    store.revoke_generation("bolt-native", "session_12345678", "profile_12345678", 1)

    with pytest.raises(RuntimeTokenError, match="invalid"):
        store.authorize_proxy(first, path="/workspace/main.py", request_id="request_12345678")
    assert store.authorize_proxy(
        other, path="/workspace/main.py", request_id="request_87654321"
    ).remaining_budget == 99


@pytest.mark.parametrize("cost", [-1, True, "1"])
def test_token_rejects_invalid_cost_before_recording_or_spending_budget(cost):
    clock = Clock(datetime(2026, 7, 12, 12, 0, tzinfo=UTC))
    store = RuntimeTokenStore(clock.now)
    token = store.issue(_claims(budget=10))
    operation = {
        "runtime_id": "bolt-native",
        "runtime_session_id": "session_12345678",
        "model_profile_id": "profile_12345678",
        "generation": 1,
        "path": "/workspace/main.py",
    }

    with pytest.raises(ValueError, match="cost"):
        store.authorize(token, cost=cost, request_id="request_12345678", **operation)

    authorization = store.authorize(token, cost=10, request_id="request_12345678", **operation)
    assert authorization.remaining_budget == 0


@pytest.mark.parametrize("request_id", ["", [], None])
def test_token_rejects_invalid_request_id_before_recording_or_spending_budget(request_id):
    clock = Clock(datetime(2026, 7, 12, 12, 0, tzinfo=UTC))
    store = RuntimeTokenStore(clock.now)
    token = store.issue(_claims(budget=10))
    operation = {
        "runtime_id": "bolt-native",
        "runtime_session_id": "session_12345678",
        "model_profile_id": "profile_12345678",
        "generation": 1,
        "path": "/workspace/main.py",
        "cost": 10,
    }

    with pytest.raises(ValueError, match="request_id"):
        store.authorize(token, request_id=request_id, **operation)

    assert store.authorize(token, request_id="request_12345678", **operation).remaining_budget == 0


def test_issue_rejects_anything_other_than_runtime_token_claims():
    store = RuntimeTokenStore(Clock(datetime(2026, 7, 12, 12, 0, tzinfo=UTC)).now)

    with pytest.raises(ValueError, match="claims"):
        store.issue({"runtime_id": "bolt-native"})


def test_issue_rejects_claims_at_or_after_expiry():
    clock = Clock(datetime(2026, 7, 12, 12, 5, tzinfo=UTC))
    store = RuntimeTokenStore(clock.now)

    with pytest.raises(RuntimeTokenError, match="expired"):
        store.issue(_claims())


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("runtime_id", "../other"),
        ("runtime_session_id", ""),
        ("model_profile_id", ""),
        ("allowed_paths", ()),
        ("allowed_paths", ("relative",)),
        ("budget", -1),
        ("budget", True),
        ("expires_at", datetime(2026, 7, 12, 12, 5)),
        ("generation", -1),
        ("generation", True),
    ],
)
def test_claims_reject_invalid_runtime_bindings(field, value):
    with pytest.raises(ValueError):
        replace(_claims(), **{field: value})


@pytest.mark.parametrize("field", ["runtime_id", "runtime_session_id", "model_profile_id"])
def test_claims_reject_non_string_identifiers(field):
    with pytest.raises(ValueError):
        replace(_claims(), **{field: None})


def test_concurrent_authorize_and_revoke_allow_at_most_one_request_then_invalidate():
    clock = Clock(datetime(2026, 7, 12, 12, 0, tzinfo=UTC))
    store = RuntimeTokenStore(clock.now)
    token = store.issue(_claims(budget=10))
    barrier = Barrier(3)
    outcomes: list[str] = []
    operation = {
        "runtime_id": "bolt-native",
        "runtime_session_id": "session_12345678",
        "model_profile_id": "profile_12345678",
        "generation": 1,
        "path": "/workspace/main.py",
        "cost": 10,
        "request_id": "request_12345678",
    }

    def authorize() -> None:
        barrier.wait()
        try:
            store.authorize(token, **operation)
            outcomes.append("authorized")
        except RuntimeTokenError:
            outcomes.append("rejected")

    def revoke() -> None:
        barrier.wait()
        store.revoke(token)

    threads = [Thread(target=authorize), Thread(target=authorize), Thread(target=revoke)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert outcomes.count("authorized") <= 1
    with pytest.raises(RuntimeTokenError, match="invalid"):
        store.authorize(token, request_id="request_87654321", **{
            key: value for key, value in operation.items() if key != "request_id"
        })


def test_proxy_authorization_derives_binding_and_cost_from_token_claims():
    clock = Clock(datetime(2026, 7, 12, 12, 0, tzinfo=UTC))
    store = RuntimeTokenStore(clock.now)
    token = store.issue(_claims(budget=2))

    first = store.authorize_proxy(token, path="/workspace/main.py", request_id="request_12345678")
    second = store.authorize_proxy(token, path="/workspace/main.py", request_id="request_87654321")

    assert first.claims.model_profile_id == "profile_12345678"
    assert first.remaining_budget == 1
    assert second.remaining_budget == 0


@pytest.mark.parametrize("path", ["/other/main.py", "/workspace/../secrets/key.txt"])
def test_proxy_authorization_rejects_path_outside_claims(path):
    store = RuntimeTokenStore(Clock(datetime(2026, 7, 12, 12, 0, tzinfo=UTC)).now)
    token = store.issue(_claims())

    with pytest.raises(RuntimeTokenError, match="path_not_allowed"):
        store.authorize_proxy(token, path=path, request_id="request_12345678")


@pytest.mark.parametrize("path", ["/workspace-other/main.py", "/workspace/../secrets/key.txt"])
def test_token_rejects_paths_outside_its_allowed_paths_without_spending_budget(path):
    clock = Clock(datetime(2026, 7, 12, 12, 0, tzinfo=UTC))
    store = RuntimeTokenStore(clock.now)
    token = store.issue(_claims())
    operation = {
        "runtime_id": "bolt-native",
        "runtime_session_id": "session_12345678",
        "model_profile_id": "profile_12345678",
        "generation": 1,
        "cost": 10,
    }

    with pytest.raises(RuntimeTokenError, match="path_not_allowed"):
        store.authorize(token, path=path, request_id="request_12345678", **operation)

    authorization = store.authorize(
        token, path="/workspace/main.py", request_id="request_87654321", **operation
    )
    assert authorization.remaining_budget == 90
