import json
import sqlite3

import pytest

from bolt_core.persistence.database import Database
from bolt_core.persistence.repositories import (
    ControlPlaneRepository,
    PersistenceConflictError,
    RuntimeEventSequenceError,
)


_SECRET_CANARY = "C4N4RY7D83CBB5XX"


def _repository(tmp_path) -> ControlPlaneRepository:
    return ControlPlaneRepository(Database.open(tmp_path / "user-data"))


def _seed_persistence_graph(repository: ControlPlaneRepository) -> str:
    workspace_id = repository.save_workspace("C:/Projects/A")
    repository.create_session("session_123", workspace_id, "active")
    repository.create_task("task_123", workspace_id, "session_123", "running", {})
    repository.create_runtime_session(
        "runtime_session_123", "task_123", "bolt-native", "external_123", "running"
    )
    return workspace_id


def _write_json_entry(repository, workspace_id, entry_point, payload) -> None:
    if entry_point == "task":
        repository.create_task("task_secret", workspace_id, "session_123", "running", payload)
    elif entry_point == "runtime-event":
        repository.append_runtime_event(
            "event_secret", "runtime_session_123", 1, "status", payload
        )
    elif entry_point == "message-metadata":
        repository.append_message(
            "message_secret", "session_123", 1, "user", "hello", None, payload
        )
    else:
        repository.save_checkpoint("checkpoint_secret", "task_123", 0, payload)


def _safe_profile_values():
    return {
        "provider": "openai-compatible",
        "base_url": "https://api.example/v1",
        "model": "model",
        "config": {},
    }


def _secret_profile_values(field):
    values = _safe_profile_values()
    secrets = {
        "config": {"apiKey": _SECRET_CANARY},
        "provider": f"password={_SECRET_CANARY}",
        "model": f"ghp_{_SECRET_CANARY}{'A' * 20}",
        "base_url": f"https://api.example/v1?api_key={_SECRET_CANARY}",
    }
    values[field] = secrets[field]
    return values


def _save_profile(repository, workspace_id, profile_id, values) -> None:
    repository.save_model_profile(
        profile_id, workspace_id, values["provider"], values["base_url"],
        values["model"], 0.2, 30.0, 8192, None, values["config"],
    )


def test_workspace_identity_is_stable_and_scoped_queries_are_isolated(tmp_path):
    repository = _repository(tmp_path)
    workspace_a = repository.save_workspace("C:/Projects/A")
    workspace_b = repository.save_workspace("C:/Projects/B")

    repository.create_session("session_a", workspace_a, "active")
    repository.create_session("session_b", workspace_b, "active")

    assert repository.list_sessions(workspace_a) == ["session_a"]
    assert repository.list_sessions(workspace_b) == ["session_b"]


@pytest.mark.parametrize(
    "workspace_path",
    [
        f"C:/Projects/sk-{_SECRET_CANARY}",
        f"C:/Projects/%73%6b-{_SECRET_CANARY}",
    ],
    ids=["raw-secret", "percent-encoded-secret"],
)
def test_workspace_path_rejects_secret_without_writing_canary(workspace_path, tmp_path):
    repository = _repository(tmp_path)

    with pytest.raises(ValueError) as caught:
        repository.save_workspace(workspace_path)

    repository.database.create_backup("after-workspace-secret")
    assert _SECRET_CANARY not in str(caught.value)
    assert _sqlite_canary_leaks(repository) == []


@pytest.mark.parametrize(
    "base_url",
    [
        f"https://sk-{_SECRET_CANARY}.example/v1",
        f"https://%73%6b-{_SECRET_CANARY}.example/v1",
        f"https://api.example/v1/Bearer%20{_SECRET_CANARY}",
    ],
    ids=["raw-host-secret", "encoded-host-secret", "encoded-bearer-path-secret"],
)
def test_model_profile_rejects_hostname_or_encoded_path_secret_without_writing_canary(
    base_url, tmp_path
):
    repository = _repository(tmp_path)
    workspace_id = repository.save_workspace("C:/Projects/A")

    with pytest.raises(ValueError) as caught:
        _save_profile(
            repository, workspace_id, "profile_url_canary",
            _safe_profile_values() | {"base_url": base_url},
        )

    repository.database.create_backup("after-url-secret")
    assert _SECRET_CANARY not in str(caught.value)
    assert _sqlite_canary_leaks(repository) == []


@pytest.mark.parametrize("reader", ["sessions", "profile"])
def test_repository_read_releases_connection_for_windows_rename(reader, tmp_path):
    repository = _repository(tmp_path)
    workspace_id = repository.save_workspace("C:/Projects/A")
    if reader == "sessions":
        repository.create_session("session_123", workspace_id, "active")
        assert repository.list_sessions(workspace_id) == ["session_123"]
    else:
        _save_profile(repository, workspace_id, "profile_123", _safe_profile_values())
        assert repository.load_model_profile("profile_123")["id"] == "profile_123"

    renamed = repository.database.path.with_name(f"{reader}-renamed.sqlite3")
    repository.database.path.rename(renamed)

    assert renamed.exists()


def test_repository_rejects_invalid_foreign_key_and_duplicate_event_sequence(tmp_path):
    repository = _repository(tmp_path)

    with pytest.raises(sqlite3.IntegrityError):
        repository.create_session("session_missing", "workspace.v1.missing", "active")

    workspace_id = repository.save_workspace("C:/Projects/A")
    repository.create_session("session_123", workspace_id, "active")
    repository.create_task("task_123", workspace_id, "session_123", "running", {})
    repository.create_runtime_session("runtime_session_123", "task_123", "bolt-native", "external_123", "running")
    repository.append_runtime_event("event_123", "runtime_session_123", 1, "status", {})

    # A duplicate sequence is now rejected before touching the database by the
    # strict-monotonic guard; the unique(runtime_session_id, sequence) constraint
    # remains as defense in depth.
    with pytest.raises(RuntimeEventSequenceError):
        repository.append_runtime_event("event_124", "runtime_session_123", 1, "status", {})


@pytest.mark.parametrize(
    "value",
    [
        ["not", "an", "object"],
        {"api_key": "«redacted:sk-…»"},
        {"nested": {"Authorization": "Bearer secret"}},
        {"note": "contains\x00nul"},
        {"endpoint": "https://example.test/?token=«redacted:sk-…"},
        {"content": "x" * 70_000},
        {"one": {"two": {"three": {"four": {"five": {"six": {"seven": {"eight": {"nine": {}}}}}}}}}},
    ],
)
def test_repository_rejects_invalid_or_sensitive_json(value, tmp_path):
    repository = _repository(tmp_path)
    workspace_id = repository.save_workspace("C:/Projects/A")
    repository.create_session("session_123", workspace_id, "active")

    with pytest.raises(ValueError, match="JSON"):
        repository.create_task("task_123", workspace_id, "session_123", "running", value)


@pytest.mark.parametrize(
    "payload",
    [
        {"apiKey": _SECRET_CANARY},
        {"x-api-key": _SECRET_CANARY},
        {"password": _SECRET_CANARY},
        {"headers": {"Cookie": _SECRET_CANARY}},
        {"privateKey": _SECRET_CANARY},
        {"items": [{"safe": {"apiKey": _SECRET_CANARY}}]},
        {"ａｐｉＫｅｙ": _SECRET_CANARY},
    ],
    ids=[
        "apiKey", "x-api-key", "password", "headers.Cookie", "privateKey", "nested-list",
        "nfkc-fullwidth-apiKey",
    ],
)
def test_task_payload_rejects_normalized_sensitive_keys_without_echoing_secret(payload, tmp_path):
    repository = _repository(tmp_path)
    workspace_id = repository.save_workspace("C:/Projects/A")
    repository.create_session("session_123", workspace_id, "active")

    with pytest.raises(ValueError) as caught:
        repository.create_task("task_123", workspace_id, "session_123", "running", payload)

    assert _SECRET_CANARY not in str(caught.value)


@pytest.mark.parametrize("sensitive_key", ["clientToken", "csrf_token"])
def test_task_payload_rejects_additional_token_keys_without_echoing_secret(
    sensitive_key, tmp_path
):
    repository = _repository(tmp_path)
    workspace_id = repository.save_workspace("C:/Projects/A")
    repository.create_session("session_123", workspace_id, "active")

    with pytest.raises(ValueError) as caught:
        repository.create_task(
            "task_123", workspace_id, "session_123", "running",
            {sensitive_key: _SECRET_CANARY},
        )

    assert _SECRET_CANARY not in str(caught.value)


@pytest.mark.parametrize("sensitive_key", ["token_value", "tokenValue"])
def test_task_payload_rejects_token_value_keys_without_echoing_secret(
    sensitive_key, tmp_path
):
    repository = _repository(tmp_path)
    workspace_id = repository.save_workspace("C:/Projects/A")
    repository.create_session("session_123", workspace_id, "active")

    with pytest.raises(ValueError) as caught:
        repository.create_task(
            "task_123", workspace_id, "session_123", "running",
            {sensitive_key: _SECRET_CANARY},
        )

    assert _SECRET_CANARY not in str(caught.value)


def test_task_payload_persists_explicit_token_usage_fields(tmp_path):
    repository = _repository(tmp_path)
    workspace_id = repository.save_workspace("C:/Projects/A")
    repository.create_session("session_123", workspace_id, "active")
    payload = {
        "token_count": 100,
        "max_tokens": 200,
        "input_tokens": 60,
        "output_tokens": 40,
        "total_tokens": 100,
    }

    repository.create_task(
        "task_usage", workspace_id, "session_123", "running", payload
    )

    with repository.database.connection() as connection:
        row = connection.execute(
            "select payload_json from tasks where id = 'task_usage'"
        ).fetchone()
    assert row is not None
    assert json.loads(row["payload_json"]) == payload


@pytest.mark.parametrize(
    "sensitive_text",
    [
        f"Authorization={_SECRET_CANARY}",
        f"Basic {_SECRET_CANARY}",
        f"Bearer {_SECRET_CANARY}",
        f"-----BEGIN PRIVATE KEY-----\n{_SECRET_CANARY}",
        f"password={_SECRET_CANARY}",
        f"access_token={_SECRET_CANARY}",
        f"ghp_{_SECRET_CANARY}{'A' * 20}",
        f"github_pat_{_SECRET_CANARY}{'A' * 66}",
        f"AIza{_SECRET_CANARY}{'A' * 19}",
        f"xoxb-{_SECRET_CANARY}",
        f"AKIA{_SECRET_CANARY}",
    ],
    ids=[
        "authorization",
        "basic",
        "bearer",
        "private-key-header",
        "password-assignment",
        "access-token-assignment",
        "github-token",
        "github-fine-grained-token",
        "google-api-key",
        "slack-token",
        "aws-access-key",
    ],
)
def test_task_payload_rejects_sensitive_text_without_echoing_secret(sensitive_text, tmp_path):
    repository = _repository(tmp_path)
    workspace_id = repository.save_workspace("C:/Projects/A")
    repository.create_session("session_123", workspace_id, "active")

    with pytest.raises(ValueError) as caught:
        repository.create_task(
            "task_123", workspace_id, "session_123", "running", {"note": sensitive_text}
        )

    assert _SECRET_CANARY not in str(caught.value)


@pytest.mark.parametrize(
    "sensitive_text",
    [
        f"OPENAI_API_KEY={_SECRET_CANARY}",
        f"client_secret={_SECRET_CANARY}",
    ],
    ids=["environment-api-key", "client-secret-assignment"],
)
def test_task_payload_rejects_additional_secret_assignments_without_echoing_secret(
    sensitive_text, tmp_path
):
    repository = _repository(tmp_path)
    workspace_id = repository.save_workspace("C:/Projects/A")
    repository.create_session("session_123", workspace_id, "active")

    with pytest.raises(ValueError) as caught:
        repository.create_task(
            "task_123", workspace_id, "session_123", "running", {"note": sensitive_text}
        )

    assert _SECRET_CANARY not in str(caught.value)


def test_rejected_secret_is_not_emitted_to_logs(caplog, tmp_path):
    repository = _repository(tmp_path)
    workspace_id = repository.save_workspace("C:/Projects/A")
    repository.create_session("session_123", workspace_id, "active")
    caplog.set_level("DEBUG")

    with pytest.raises(ValueError) as caught:
        repository.create_task(
            "task_123", workspace_id, "session_123", "running", {"api_key": _SECRET_CANARY}
        )

    assert _SECRET_CANARY not in str(caught.value)
    assert _SECRET_CANARY not in caplog.text


@pytest.mark.parametrize(
    "entry_point",
    ["task", "runtime-event", "message-metadata", "checkpoint-payload"],
)
@pytest.mark.parametrize(
    "payload",
    [
        {"apiKey": _SECRET_CANARY},
        {"note": f"access_token={_SECRET_CANARY}"},
    ],
    ids=["sensitive-key", "sensitive-value"],
)
def test_every_json_repository_entry_rejects_sensitive_keys_and_values(
    entry_point, payload, tmp_path
):
    repository = _repository(tmp_path)
    workspace_id = _seed_persistence_graph(repository)

    with pytest.raises(ValueError) as caught:
        _write_json_entry(repository, workspace_id, entry_point, payload)

    assert _SECRET_CANARY not in str(caught.value)


def test_model_profile_stores_credential_reference_but_not_secret(tmp_path):
    repository = _repository(tmp_path)
    workspace_id = repository.save_workspace("C:/Projects/A")

    repository.save_model_profile(
        "profile_123", workspace_id, "openai-compatible", "https://api.example/v1",
        "model", 0.2, 30.0, 8192, "wincred.v1.123", {},
    )

    assert repository.load_model_profile("profile_123")["credential_id"] == "wincred.v1.123"
    secret = b"sk-abc123def456ghi789jkl012mno345"
    files = [
        repository.database.path,
        repository.database.path.with_name(f"{repository.database.path.name}-wal"),
        repository.database.path.with_name(f"{repository.database.path.name}-shm"),
    ]
    assert all(secret not in path.read_bytes() for path in files if path.exists())


@pytest.mark.parametrize("credential_id", ["sk-secret", "Bearer secret", "contains\x00nul"])
def test_model_profile_rejects_a_secret_or_control_character_as_credential_reference(
    credential_id, tmp_path
):
    repository = _repository(tmp_path)
    workspace_id = repository.save_workspace("C:/Projects/A")

    with pytest.raises(ValueError, match="credential reference"):
        repository.save_model_profile(
            "profile_123", workspace_id, "openai-compatible", "https://api.example/v1",
            "model", 0.2, 30.0, 8192, credential_id, {},
        )


@pytest.mark.parametrize("operation", ["save", "update"])
@pytest.mark.parametrize(
    "changes",
    [
        {"base_url": f"https://user:{_SECRET_CANARY}@api.example/v1"},
        {"base_url": f"https://api.example/v1?access_token={_SECRET_CANARY}"},
        {"base_url": f"https://api.example/v1?api_key={_SECRET_CANARY}"},
        {"base_url": f"https://api.example/v1?password={_SECRET_CANARY}"},
        {"base_url": f"https://api.example/v1#{_SECRET_CANARY}"},
        {"base_url": f"file:///C:/tmp/{_SECRET_CANARY}"},
        {"base_url": f"ftp://api.example/{_SECRET_CANARY}"},
        {"base_url": f"https://api.example/v1?%61pi_key={_SECRET_CANARY}"},
        {"base_url": f"https://api.example/v1?access%5Ftoken={_SECRET_CANARY}"},
        {
            "base_url": (
                f"https://api.example/v1?mode=safe&mode=still-safe&api_key={_SECRET_CANARY}"
            )
        },
        {"config": {"apiKey": _SECRET_CANARY}},
        {"provider": f"password={_SECRET_CANARY}"},
        {"model": f"ghp_{_SECRET_CANARY}{'A' * 20}"},
    ],
    ids=[
        "userinfo",
        "access-token-query",
        "api-key-query",
        "password-query",
        "fragment",
        "file-scheme",
        "ftp-scheme",
        "percent-encoded-api-key",
        "percent-encoded-access-token",
        "repeated-query-late-sensitive-key",
        "config-key",
        "provider-assignment",
        "model-credential-prefix",
    ],
)
def test_model_profile_rejects_sensitive_fields_on_save_and_update(operation, changes, tmp_path):
    repository = _repository(tmp_path)
    workspace_id = repository.save_workspace("C:/Projects/A")
    if operation == "update":
        _save_profile(repository, workspace_id, "profile_123", _safe_profile_values())

    with pytest.raises(ValueError) as caught:
        if operation == "save":
            _save_profile(
                repository, workspace_id, "profile_123", _safe_profile_values() | changes
            )
        else:
            repository.update_model_profile("profile_123", 0, changes)

    assert _SECRET_CANARY not in str(caught.value)


@pytest.mark.parametrize("operation", ["save", "update"])
@pytest.mark.parametrize(
    "query_value",
    [
        f"ghp_{_SECRET_CANARY}{'A' * 20}",
        f"sk-{_SECRET_CANARY}",
        f"Bearer%20ghp_{_SECRET_CANARY}{'A' * 20}",
        f"password={_SECRET_CANARY}",
        f"safe;api_key=ghp_{_SECRET_CANARY}{'A' * 20}",
    ],
    ids=[
        "github-token",
        "openai-token",
        "encoded-bearer-github-token",
        "nested-password-assignment",
        "semicolon-api-key-assignment",
    ],
)
def test_model_profile_rejects_credentials_in_safe_query_values_atomically(
    operation, query_value, tmp_path
):
    repository = _repository(tmp_path)
    workspace_id = repository.save_workspace("C:/Projects/A")
    original = None
    if operation == "update":
        _save_profile(repository, workspace_id, "profile_123", _safe_profile_values())
        original = repository.load_model_profile("profile_123")
    base_url = f"https://api.example/v1?mode={query_value}"

    with pytest.raises(ValueError) as caught:
        if operation == "save":
            _save_profile(
                repository, workspace_id, "profile_123",
                _safe_profile_values() | {"base_url": base_url},
            )
        else:
            repository.update_model_profile("profile_123", 0, {"base_url": base_url})

    assert _SECRET_CANARY not in str(caught.value)
    if operation == "save":
        with pytest.raises(KeyError):
            repository.load_model_profile("profile_123")
    else:
        assert repository.load_model_profile("profile_123") == original


@pytest.mark.parametrize("operation", ["save", "update"])
@pytest.mark.parametrize(
    "base_url",
    [
        f"https://api.example/v1/sk-{_SECRET_CANARY}",
        f"https://api.example/v1/%73%6b-{_SECRET_CANARY}",
        f"https://api.example/v1/%2573%256b-{_SECRET_CANARY}",
    ],
    ids=["raw-path-credential", "encoded-path-credential", "double-encoded-path-credential"],
)
def test_model_profile_rejects_path_credentials_without_writing_canary(
    operation, base_url, tmp_path
):
    repository = _repository(tmp_path)
    workspace_id = repository.save_workspace("C:/Projects/A")
    original = None
    if operation == "update":
        _save_profile(repository, workspace_id, "profile_123", _safe_profile_values())
        original = repository.load_model_profile("profile_123")

    with pytest.raises(ValueError) as caught:
        if operation == "save":
            _save_profile(repository, workspace_id, "profile_path_canary", _safe_profile_values() | {"base_url": base_url})
        else:
            repository.update_model_profile("profile_123", 0, {"base_url": base_url})

    repository.database.create_backup("after-path-secret")
    assert _SECRET_CANARY not in str(caught.value)
    assert _sqlite_canary_leaks(repository) == []
    if operation == "save":
        with pytest.raises(KeyError):
            repository.load_model_profile("profile_path_canary")
    else:
        assert repository.load_model_profile("profile_123") == original


@pytest.mark.parametrize("operation", ["save", "update"])
@pytest.mark.parametrize(
    "base_url",
    [
        f"https://api.example/v1\nsafe-{_SECRET_CANARY}",
        f"https://api.example/v1\x1fsafe-{_SECRET_CANARY}",
        f"https://api.example:99999/v1?mode={_SECRET_CANARY}",
        f"https://api.example/v1?api%255fkey={_SECRET_CANARY}",
        f"https://api.example:0/v1?mode={_SECRET_CANARY}",
        f"https://999.999.999.999/v1?mode={_SECRET_CANARY}",
    ],
    ids=[
        "newline",
        "control-character",
        "invalid-port",
        "double-encoded-api-key",
        "zero-port",
        "invalid-numeric-ip",
    ],
)
def test_model_profile_rejects_malformed_base_url_without_echoing_secret(
    operation, base_url, tmp_path
):
    repository = _repository(tmp_path)
    workspace_id = repository.save_workspace("C:/Projects/A")
    if operation == "update":
        _save_profile(repository, workspace_id, "profile_123", _safe_profile_values())

    with pytest.raises(ValueError) as caught:
        if operation == "save":
            _save_profile(
                repository, workspace_id, "profile_123",
                _safe_profile_values() | {"base_url": base_url},
            )
        else:
            repository.update_model_profile("profile_123", 0, {"base_url": base_url})

    assert _SECRET_CANARY not in str(caught.value)


@pytest.mark.parametrize("operation", ["save", "update"])
@pytest.mark.parametrize(
    "base_url",
    [
        "https://user%3Apass%40api.example/v1",
        f"https://api.example/v1?api%252525255Fkey={_SECRET_CANARY}",
        "https://api example/v1",
    ],
    ids=["encoded-userinfo", "five-layer-encoded-query-key", "space-in-host"],
)
def test_model_profile_rejects_ambiguous_url_authority_and_raw_query_key(
    operation, base_url, tmp_path
):
    repository = _repository(tmp_path)
    workspace_id = repository.save_workspace("C:/Projects/A")
    if operation == "update":
        _save_profile(repository, workspace_id, "profile_123", _safe_profile_values())

    with pytest.raises(ValueError) as caught:
        if operation == "save":
            _save_profile(
                repository, workspace_id, "profile_123",
                _safe_profile_values() | {"base_url": base_url},
            )
        else:
            repository.update_model_profile("profile_123", 0, {"base_url": base_url})

    assert _SECRET_CANARY not in str(caught.value)


def _write_canary_case(repository, workspace_id, case) -> None:
    json_entries = {"task", "runtime-event", "message-metadata", "checkpoint-payload"}
    if case in json_entries:
        _write_json_entry(repository, workspace_id, case, {"apiKey": _SECRET_CANARY})
        return
    _, operation, field = case.split("-", 2)
    values = _secret_profile_values(field)
    if operation == "save":
        _save_profile(repository, workspace_id, "profile_secret", values)
        return
    _save_profile(repository, workspace_id, "profile_123", _safe_profile_values())
    repository.update_model_profile("profile_123", 0, {field: values[field]})


def _sqlite_canary_leaks(repository):
    path = repository.database.path
    candidates = [
        path,
        path.with_name(f"{path.name}-wal"),
        path.with_name(f"{path.name}-shm"),
        *sorted((path.parent / "backups").glob("*.sqlite3")),
    ]
    canary = _SECRET_CANARY.encode()
    return [item.name for item in candidates if item.exists() and canary in item.read_bytes()]


def _has_partial_row(repository, case):
    targets = {
        "task": ("tasks", "task_secret"),
        "runtime-event": ("runtime_events", "event_secret"),
        "message-metadata": ("messages", "message_secret"),
        "checkpoint-payload": ("checkpoints", "checkpoint_secret"),
    }
    with repository.database.connection() as connection:
        if case.startswith("profile-update"):
            row = connection.execute(
                "select provider, base_url, model, config_json, revision "
                "from model_profiles where id = 'profile_123'"
            ).fetchone()
            return tuple(row) != (
                "openai-compatible", "https://api.example/v1", "model", "{}", 0,
            )
        table, record_id = targets.get(case, ("model_profiles", "profile_secret"))
        return connection.execute(
            f"select 1 from {table} where id = ?", (record_id,)
        ).fetchone() is not None


@pytest.mark.parametrize(
    "case",
    [
        "task", "runtime-event", "message-metadata", "checkpoint-payload",
        "profile-save-config", "profile-save-provider", "profile-save-model",
        "profile-save-base_url", "profile-update-config", "profile-update-provider",
        "profile-update-model", "profile-update-base_url",
    ],
)
def test_rejected_secret_leaves_no_disk_bytes_or_partial_row(case, tmp_path):
    repository = _repository(tmp_path)
    workspace_id = _seed_persistence_graph(repository)
    rejection = None

    try:
        _write_canary_case(repository, workspace_id, case)
    except (ValueError, AttributeError) as error:
        rejection = error

    repository.database.create_backup("after-rejected-secret")
    assert {
        "leaked_files": _sqlite_canary_leaks(repository),
        "partial_row": _has_partial_row(repository, case),
        "rejection_type": type(rejection).__name__,
    } == {"leaked_files": [], "partial_row": False, "rejection_type": "ValueError"}
    assert _SECRET_CANARY not in str(rejection)


def test_workspace_path_containing_risk_management_is_persisted(tmp_path):
    repository = _repository(tmp_path)

    workspace_id = repository.save_workspace(tmp_path / "risk-management")

    with repository.database.connection() as connection:
        row = connection.execute(
            "select canonical_path from workspaces where workspace_id = ?", (workspace_id,)
        ).fetchone()
    assert row is not None
    assert row["canonical_path"].endswith("risk-management")


def test_message_content_containing_basic_risk_management_guide_is_persisted(tmp_path):
    repository = _repository(tmp_path)
    _seed_persistence_graph(repository)
    content = "Basic usage guide for risk-management"

    repository.append_message(
        "message_safe", "session_123", 1, "user", content, None, {}
    )

    with repository.database.connection() as connection:
        row = connection.execute(
            "select content from messages where id = 'message_safe'"
        ).fetchone()
    assert row is not None
    assert row["content"] == content


@pytest.mark.parametrize(
    "content",
    [
        "Basic configuration guide",
        "basic principles only",
        "Bearer token is explained",
        "Basic configuration",
        "Bearer explanation",
    ],
    ids=[
        "basic-configuration",
        "basic-principles",
        "bearer-explanation",
        "basic-configuration-short",
        "bearer-explanation-short",
    ],
)
def test_message_content_allows_basic_and_bearer_in_normal_sentences(content, tmp_path):
    repository = _repository(tmp_path)
    _seed_persistence_graph(repository)

    repository.append_message(
        "message_safe", "session_123", 1, "user", content, None, {}
    )

    with repository.database.connection() as connection:
        row = connection.execute(
            "select content from messages where id = 'message_safe'"
        ).fetchone()
    assert row is not None
    assert row["content"] == content


@pytest.mark.parametrize(
    "content", [f"Basic {_SECRET_CANARY}", f"Bearer {_SECRET_CANARY}"],
    ids=["basic-credential", "bearer-credential"],
)
def test_message_content_rejects_complete_basic_and_bearer_credentials(content, tmp_path):
    repository = _repository(tmp_path)
    _seed_persistence_graph(repository)

    with pytest.raises(ValueError) as caught:
        repository.append_message(
            "message_secret", "session_123", 1, "user", content, None, {}
        )

    assert _SECRET_CANARY not in str(caught.value)


def test_model_profile_allows_safe_provider_and_model_containing_risk_model(tmp_path):
    repository = _repository(tmp_path)
    workspace_id = repository.save_workspace("C:/Projects/A")
    values = _safe_profile_values() | {
        "provider": "risk-model-provider",
        "model": "risk-model",
    }

    _save_profile(repository, workspace_id, "profile_safe", values)

    profile = repository.load_model_profile("profile_safe")
    assert profile["provider"] == "risk-model-provider"
    assert profile["model"] == "risk-model"


def test_model_profile_revision_conflict_preserves_previous_value(tmp_path):
    repository = _repository(tmp_path)
    workspace_id = repository.save_workspace("C:/Projects/A")
    repository.save_model_profile(
        "profile_123", workspace_id, "openai-compatible", "https://api.example/v1",
        "model", 0.2, 30.0, 8192, None, {},
    )

    with pytest.raises(PersistenceConflictError):
        repository.update_model_profile("profile_123", 7, {"model": "other"})

    assert repository.load_model_profile("profile_123")["model"] == "model"


def test_model_profile_revision_at_sqlite_limit_cannot_be_incremented(tmp_path):
    repository = _repository(tmp_path)
    workspace_id = repository.save_workspace("C:/Projects/A")
    _save_profile(repository, workspace_id, "profile_123", _safe_profile_values())
    with repository.database.transaction() as connection:
        connection.execute(
            "update model_profiles set revision = ? where id = ?", (2**63 - 1, "profile_123"),
        )

    with pytest.raises(PersistenceConflictError):
        repository.update_model_profile("profile_123", 2**63 - 1, {"model": "other"})

    profile = repository.load_model_profile("profile_123")
    assert profile["revision"] == 2**63 - 1
    assert profile["model"] == "model"


@pytest.mark.parametrize(
    ("entry_point", "invalid_value", "disk_marker"),
    [
        ("task", float("nan"), b"NaN"),
        ("task", float("inf"), b"Infinity"),
        ("task", float("-inf"), b"-Infinity"),
        ("runtime-event", float("nan"), b"NaN"),
        ("runtime-event", float("inf"), b"Infinity"),
        ("runtime-event", float("-inf"), b"-Infinity"),
        ("message-metadata", float("nan"), b"NaN"),
        ("message-metadata", float("inf"), b"Infinity"),
        ("message-metadata", float("-inf"), b"-Infinity"),
        ("checkpoint-payload", float("nan"), b"NaN"),
        ("checkpoint-payload", float("inf"), b"Infinity"),
        ("checkpoint-payload", float("-inf"), b"-Infinity"),
    ],
    ids=[
        "task-nan", "task-inf", "task-negative-inf",
        "runtime-nan", "runtime-inf", "runtime-negative-inf",
        "message-nan", "message-inf", "message-negative-inf",
        "checkpoint-nan", "checkpoint-inf", "checkpoint-negative-inf",
    ],
)
def test_json_repository_entries_reject_non_finite_numbers_before_writing(
    entry_point, invalid_value, disk_marker, tmp_path
):
    repository = _repository(tmp_path)
    workspace_id = _seed_persistence_graph(repository)

    with pytest.raises(ValueError):
        _write_json_entry(repository, workspace_id, entry_point, {"value": invalid_value})

    repository.database.create_backup("after-non-finite-json")
    assert _sqlite_bytes_containing(repository, disk_marker) == []


@pytest.mark.parametrize("invalid_sequence", [True, 1.5, "1", -1])
@pytest.mark.parametrize("entry_point", ["runtime-event", "message", "checkpoint"])
def test_runtime_message_and_checkpoint_reject_invalid_integer_counters(
    entry_point, invalid_sequence, tmp_path
):
    repository = _repository(tmp_path)
    _seed_persistence_graph(repository)

    with pytest.raises(ValueError):
        if entry_point == "runtime-event":
            repository.append_runtime_event(
                "event_invalid_sequence", "runtime_session_123", invalid_sequence,
                "status", {},
            )
        elif entry_point == "message":
            repository.append_message(
                "message_invalid_sequence", "session_123", invalid_sequence,
                "user", "hello", None, {},
            )
        else:
            repository.save_checkpoint(
                "checkpoint_invalid_revision", "task_123", invalid_sequence, {},
            )


@pytest.mark.parametrize("entry_point", ["runtime-event", "message"])
def test_runtime_and_message_sequence_reject_zero_before_writing(entry_point, tmp_path):
    repository = _repository(tmp_path)
    _seed_persistence_graph(repository)

    with pytest.raises(ValueError):
        if entry_point == "runtime-event":
            repository.append_runtime_event(
                "event_zero_sequence", "runtime_session_123", 0, "status", {},
            )
        else:
            repository.append_message(
                "message_zero_sequence", "session_123", 0, "user", "hello", None, {},
            )


@pytest.mark.parametrize("entry_point", ["runtime-event", "message", "checkpoint"])
def test_sqlite_integer_counters_reject_overflow_before_writing(entry_point, tmp_path):
    repository = _repository(tmp_path)
    _seed_persistence_graph(repository)

    with pytest.raises(ValueError):
        if entry_point == "runtime-event":
            repository.append_runtime_event(
                "event_large_sequence", "runtime_session_123", 2**63, "status", {},
            )
        elif entry_point == "message":
            repository.append_message(
                "message_large_sequence", "session_123", 2**63, "user", "hello", None, {},
            )
        else:
            repository.save_checkpoint(
                "checkpoint_large_revision", "task_123", 2**63, {},
            )


@pytest.mark.parametrize("invalid_revision", [True, 0.0, "0", -1, 2**63])
def test_model_profile_rejects_invalid_expected_revision_before_update(
    invalid_revision, tmp_path
):
    repository = _repository(tmp_path)
    workspace_id = repository.save_workspace("C:/Projects/A")
    _save_profile(repository, workspace_id, "profile_123", _safe_profile_values())
    original = repository.load_model_profile("profile_123")

    with pytest.raises(ValueError):
        repository.update_model_profile(
            "profile_123", invalid_revision, {"model": "other"}
        )

    assert repository.load_model_profile("profile_123") == original


def test_model_profile_requires_provider_slug_but_allows_model_and_credential_dots(tmp_path):
    repository = _repository(tmp_path)
    workspace_id = repository.save_workspace("C:/Projects/A")

    with pytest.raises(ValueError):
        repository.save_model_profile(
            "profile_provider_dot", workspace_id, "openai.v1", "https://api.example/v1",
            "gpt-4o", 0.2, 30.0, 8192, "wincred.v1.123", {},
        )

    repository.save_model_profile(
        "profile_safe_format", workspace_id, "openai-compatible", "https://api.example/v1",
        "gpt-4o", 0.2, 30.0, 8192, "wincred.v1.123", {},
    )


@pytest.mark.parametrize("operation", ["save", "update"])
def test_context_window_rejects_sqlite_integer_overflow(operation, tmp_path):
    repository = _repository(tmp_path)
    workspace_id = repository.save_workspace("C:/Projects/A")
    original = None
    if operation == "update":
        _save_profile(repository, workspace_id, "profile_123", _safe_profile_values())
        original = repository.load_model_profile("profile_123")

    with pytest.raises(ValueError):
        if operation == "save":
            repository.save_model_profile(
                "profile_large_window", workspace_id, "openai-compatible",
                "https://api.example/v1", "gpt-4o", 0.2, 30.0, 2**63,
                "wincred.v1.123", {},
            )
        else:
            repository.update_model_profile("profile_123", 0, {"context_window": 2**63})

    if operation == "save":
        with pytest.raises(KeyError):
            repository.load_model_profile("profile_large_window")
    else:
        assert repository.load_model_profile("profile_123") == original


@pytest.mark.parametrize("operation", ["save", "update"])
@pytest.mark.parametrize(
    ("field", "invalid_value"),
    [
        ("temperature", "not-a-number"),
        ("temperature", True),
        ("temperature", float("nan")),
        ("temperature", float("inf")),
        ("temperature", float("-inf")),
        ("temperature", -0.1),
        ("timeout", "not-a-number"),
        ("timeout", True),
        ("timeout", float("nan")),
        ("timeout", float("inf")),
        ("timeout", float("-inf")),
        ("timeout", -0.1),
        ("timeout", 0),
        ("context_window", True),
        ("context_window", 1.5),
        ("context_window", "8192"),
        ("context_window", 0),
        ("context_window", -1),
    ],
    ids=[
        "temperature-string", "temperature-bool", "temperature-nan",
        "temperature-inf", "temperature-negative-inf", "temperature-negative",
        "timeout-string", "timeout-bool", "timeout-nan", "timeout-inf",
        "timeout-negative-inf", "timeout-negative", "timeout-zero",
        "context-window-bool", "context-window-float", "context-window-string",
        "context-window-zero", "context-window-negative",
    ],
)
def test_model_profile_rejects_invalid_numeric_settings_on_save_and_update(
    operation, field, invalid_value, tmp_path
):
    repository = _repository(tmp_path)
    workspace_id = repository.save_workspace("C:/Projects/A")
    original = None
    if operation == "update":
        _save_profile(repository, workspace_id, "profile_123", _safe_profile_values())
        original = repository.load_model_profile("profile_123")

    with pytest.raises(ValueError):
        if operation == "save":
            repository.save_model_profile(
                "profile_invalid", workspace_id, "openai-compatible",
                "https://api.example/v1", "model",
                invalid_value if field == "temperature" else 0.2,
                invalid_value if field == "timeout" else 30.0,
                invalid_value if field == "context_window" else 8192,
                None, {},
            )
        else:
            repository.update_model_profile("profile_123", 0, {field: invalid_value})

    if operation == "save":
        with pytest.raises(KeyError):
            repository.load_model_profile("profile_invalid")
    else:
        assert repository.load_model_profile("profile_123") == original


@pytest.mark.parametrize("operation", ["save", "update"])
@pytest.mark.parametrize("field", ["provider", "model", "credential_id"])
@pytest.mark.parametrize("invalid_kind", ["url", "userinfo", "illegal"])
def test_model_profile_rejects_non_identifier_text_without_persisting_canary(
    operation, field, invalid_kind, tmp_path
):
    repository = _repository(tmp_path)
    workspace_id = repository.save_workspace("C:/Projects/A")
    original = None
    if operation == "update":
        _save_profile(repository, workspace_id, "profile_123", _safe_profile_values())
        original = repository.load_model_profile("profile_123")
    invalid_value = {
        "url": f"https://{field}.example/{_SECRET_CANARY}",
        "userinfo": f"user:{_SECRET_CANARY}@example",
        "illegal": f"invalid {field} {_SECRET_CANARY}",
    }[invalid_kind]

    with pytest.raises(ValueError) as caught:
        if operation == "save":
            values = _safe_profile_values() | {field: invalid_value}
            repository.save_model_profile(
                "profile_canary", workspace_id, values["provider"], values["base_url"],
                values["model"], 0.2, 30.0, 8192, values.get("credential_id"),
                values["config"],
            )
        else:
            repository.update_model_profile("profile_123", 0, {field: invalid_value})

    repository.database.create_backup("after-invalid-identifier")
    assert _SECRET_CANARY not in str(caught.value)
    assert _sqlite_canary_leaks(repository) == []
    if operation == "save":
        with pytest.raises(KeyError):
            repository.load_model_profile("profile_canary")
    else:
        assert repository.load_model_profile("profile_123") == original


def _sqlite_bytes_containing(repository, marker: bytes) -> list[str]:
    path = repository.database.path
    candidates = [
        path,
        path.with_name(f"{path.name}-wal"),
        path.with_name(f"{path.name}-shm"),
        *sorted((path.parent / "backups").glob("*.sqlite3")),
    ]
    return [item.name for item in candidates if item.exists() and marker in item.read_bytes()]
