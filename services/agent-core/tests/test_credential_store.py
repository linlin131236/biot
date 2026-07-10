import pytest

from bolt_core.credential_store import InMemoryCredentialStore


def test_in_memory_credentials_are_isolated_by_id():
    store = InMemoryCredentialStore()
    store.save("model.openai", "openai-secret")
    store.save("model.proxy", "proxy-secret")

    assert store.load("model.openai") == "openai-secret"
    assert store.load("model.proxy") == "proxy-secret"


def test_delete_removes_only_requested_credential():
    store = InMemoryCredentialStore({"a": "one", "b": "two"})

    store.delete("a")

    assert store.exists("a") is False
    assert store.load("b") == "two"


def test_exists_and_load_report_missing_and_saved_credentials():
    store = InMemoryCredentialStore()

    assert store.exists("model.openai") is False
    assert store.load("model.openai") is None

    store.save("model.openai", "openai-secret")

    assert store.exists("model.openai") is True
    assert store.load("model.openai") == "openai-secret"


@pytest.mark.parametrize(
    "values",
    [{"": "secret"}, {"id": ""}],
)
def test_initial_values_reject_empty_credential_id_or_secret(values):
    with pytest.raises(ValueError, match="credential id and secret are required"):
        InMemoryCredentialStore(values)


def test_initial_values_and_store_are_isolated():
    values = {"existing": "original"}
    store = InMemoryCredentialStore(values)

    values["existing"] = "caller-updated"
    store.save("saved", "store-secret")

    assert store.load("existing") == "original"
    assert "saved" not in values


@pytest.mark.parametrize(
    ("credential_id", "secret"),
    [("", "secret"), ("model.openai", "")],
)
def test_save_rejects_empty_credential_id_or_secret(credential_id, secret):
    store = InMemoryCredentialStore()

    with pytest.raises(ValueError, match="credential id and secret are required"):
        store.save(credential_id, secret)
