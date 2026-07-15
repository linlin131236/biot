from __future__ import annotations

import json
from threading import Event, RLock, Thread
from time import sleep

import pytest

from bolt_core.runtime.acp_stdio import AcpStdioClient, AcpTransportError


class _Sink:
    def __init__(self) -> None:
        self.writes: list[bytes] = []

    def write(self, value: bytes) -> None:
        self.writes.append(value)
        sleep(0.05)
    def flush(self) -> None:
        pass


class _BlockingOutput:
    def __init__(self) -> None:
        self.release = Event()

    def readline(self, _limit: int = -1) -> bytes:
        self.release.wait(2)
        return b""


class _Process:
    def __init__(self) -> None:
        self.stdin = _Sink()
        self.stdout = _BlockingOutput()
        self.stderr = None
    @staticmethod
    def poll():
        return None


def test_concurrent_responders_produce_one_terminal_response():
    process = _Process()
    client = AcpStdioClient(process, lambda _message: None, lambda *_args: None)
    with client._inbound_lock:
        client._inbound_requests.add(77)
    client._write_lock.acquire()
    outcomes = []

    def respond(label: str) -> None:
        try:
            client.respond(77, {"source": label})
            outcomes.append("ok")
        except ValueError:
            outcomes.append("rejected")

    first = Thread(target=respond, args=("first",))
    second = Thread(target=respond, args=("second",))
    first.start()
    second.start()
    sleep(0.05)
    client._write_lock.release()
    first.join(2)
    second.join(2)
    process.stdout.release.set()

    assert sorted(outcomes) == ["ok", "rejected"]
    assert len(process.stdin.writes) == 1
    assert json.loads(process.stdin.writes[0])["id"] == 77


def test_close_cannot_publish_lifecycle_before_owned_response_write():
    process = _Process()
    write_ready, release_write, progress = Event(), Event(), Event()
    order, gate = [], RLock()
    class ObservedLock:
        def __enter__(self):
            if not gate.acquire(blocking=False):
                progress.set()
                gate.acquire()
            return self

        def __exit__(self, *_args):
            gate.release()
    client = AcpStdioClient(process, lambda _message: None, lambda *_args: None,
                            lambda _error: (order.append("lifecycle"), progress.set()))
    with client._inbound_lock:
        client._inbound_requests.add(7)
    def paused_write(encoded, write=client._write_encoded):
        write_ready.set()
        assert release_write.wait(1)
        order.append("response")
        write(encoded)
    client._write_lock = ObservedLock()
    client._write_encoded = paused_write
    responding = Thread(target=client.respond, args=(7, {"ok": True}))
    closing = Thread(target=client.close)
    responding.start()
    assert write_ready.wait(1)
    closing.start()
    assert progress.wait(1)
    release_write.set()
    responding.join(1)
    closing.join(1)
    process.stdout.release.set()
    assert not responding.is_alive() and not closing.is_alive()
    assert order == ["response", "lifecycle"]


def test_close_between_check_and_registration_wakes_request():
    process = _Process()
    client = AcpStdioClient(process, lambda _message: None, lambda *_args: None)
    checked, release = Event(), Event()
    original_check = client._raise_if_closed
    outcomes = []

    def paused_check():
        original_check()
        checked.set()
        release.wait(2)

    client._raise_if_closed = paused_check

    def request():
        try:
            client.request("session/prompt", {}, timeout=0.5)
        except Exception as error:
            outcomes.append(error)

    thread = Thread(target=request)
    thread.start()
    assert checked.wait(1)
    closing = Thread(target=client.close)
    closing.start()
    release.set()
    thread.join(2)
    closing.join(2)
    process.stdout.release.set()

    assert len(outcomes) == 1
    assert str(outcomes[0]) == "ACP transport closed"


def test_close_before_registered_handler_runs_prevents_business_and_response(monkeypatch):
    process = _Process()
    registered, release_start, handler_finished = Event(), Event(), Event()
    handled, lifecycle_called = Event(), Event()
    lifecycle, real_thread = [], Thread

    def on_lifecycle(error):
        lifecycle.append(str(error))
        lifecycle_called.set()

    client = AcpStdioClient(
        process, lambda _message: None, lambda *_args: handled.set(), on_lifecycle,
    )

    class PausedStartThread:
        def __init__(self, *, target, args, daemon):
            def run():
                try:
                    target(*args)
                finally:
                    handler_finished.set()

            self._thread = real_thread(target=run, daemon=daemon)

        def start(self):
            registered.set()
            assert release_start.wait(1)
            self._thread.start()

    monkeypatch.setattr("bolt_core.runtime.acp_stdio.Thread", PausedStartThread)
    request = {"jsonrpc": "2.0", "id": 90, "method": "_bolt/model.complete", "params": {}}
    receiving = real_thread(target=client._receive_request, args=(request,))
    receiving.start()
    assert registered.wait(1)
    client.close()
    assert lifecycle_called.wait(1)
    release_start.set()
    receiving.join(1)
    assert handler_finished.wait(1)
    process.stdout.release.set()

    assert not receiving.is_alive()
    assert not handled.is_set()
    assert process.stdin.writes == []
    assert client._failure is not None
    assert str(client._failure) == "ACP transport closed"
    assert lifecycle == ["ACP transport closed"]


def test_closed_transport_rejects_new_inbound_request():
    process = _Process()
    handled = Event()
    client = AcpStdioClient(process, lambda _message: None, lambda *_args: handled.set())
    client.close()
    client._receive_request({
        "jsonrpc": "2.0", "id": 91, "method": "_bolt/model.complete", "params": {},
    })
    process.stdout.release.set()

    assert not handled.wait(0.1)
    assert client._inbound_requests == set()


def test_error_response_replaces_untrusted_message():
    process = _Process()
    client = AcpStdioClient(process, lambda _message: None, lambda *_args: None)
    with client._inbound_lock:
        client._inbound_requests.add(9)

    client.respond_error(9, -32603, "authorization-secret-canary")
    process.stdout.release.set()

    response = json.loads(process.stdin.writes[0])
    assert response["error"] == {"code": -32603, "message": "Internal error"}
    assert "canary" not in json.dumps(response)


def test_oversized_handler_result_returns_generic_error():
    process = _Process()

    def handler(client, message):
        client.respond(message["id"], {"value": "x" * 1_100_000})

    client = AcpStdioClient(process, lambda _message: None, handler)
    client._receive_request({
        "jsonrpc": "2.0", "id": 10, "method": "_bolt/model.complete", "params": {},
    })
    sleep(0.2)
    process.stdout.release.set()

    assert len(process.stdin.writes) == 1
    response = json.loads(process.stdin.writes[0])
    assert response["error"] == {"code": -32603, "message": "Internal error"}


def test_reused_id_is_not_completed_by_prior_handler_cleanup():
    process = _Process()
    first_responded, release_first, first_finished = Event(), Event(), Event()
    second_started, release_second, second_responded = Event(), Event(), Event()

    def handler(client, message):
        generation = message["params"]["generation"]
        if generation == 1:
            client.respond(message["id"], {"generation": 1})
            first_responded.set()
            release_first.wait(2)
            return
        second_started.set()
        release_second.wait(2)
        client.respond(message["id"], {"generation": 2})
        second_responded.set()

    client = AcpStdioClient(process, lambda _message: None, handler)
    handle_request = client._handle_request
    def observed_handle(message, token):
        handle_request(message, token)
        if message["params"]["generation"] == 1:
            first_finished.set()
    client._handle_request = observed_handle
    request = {"jsonrpc": "2.0", "id": 41, "method": "_bolt/model.complete"}
    client._receive_request({**request, "params": {"generation": 1}})
    assert first_responded.wait(1)
    client._receive_request({**request, "params": {"generation": 2}})
    assert second_started.wait(1)
    release_first.set()
    assert first_finished.wait(1)
    release_second.set()
    assert second_responded.wait(1)
    process.stdout.release.set()
    responses = [json.loads(line) for line in process.stdin.writes]
    assert [item["result"]["generation"] for item in responses] == [1, 2]


def test_lifecycle_handler_can_reenter_request_after_broken_pipe():
    process = _Process()
    process.stdin.write = lambda _value: (_ for _ in ()).throw(BrokenPipeError())
    lifecycle_returned = Event()
    outcomes = []

    def lifecycle(_error):
        try:
            client.request("session/prompt", {}, timeout=0.1)
        except AcpTransportError as error:
            outcomes.append(str(error))
        finally:
            lifecycle_returned.set()

    client = AcpStdioClient(process, lambda _message: None, lambda *_args: None, lifecycle)

    def request():
        try:
            client.request("session/prompt", {}, timeout=0.1)
        except AcpTransportError as error:
            outcomes.append(str(error))

    thread = Thread(target=request, daemon=True)
    thread.start()
    assert lifecycle_returned.wait(1)
    thread.join(1)
    process.stdout.release.set()
    assert not thread.is_alive()
    assert outcomes.count("ACP transport write failed") == 2


def test_lifecycle_handler_exception_cannot_replace_transport_failure():
    process = _Process()
    process.stdin.write = lambda _value: (_ for _ in ()).throw(BrokenPipeError())
    canary = "lifecycle-secret-canary"
    lifecycle_errors = []

    def lifecycle(error):
        lifecycle_errors.append(str(error))
        raise RuntimeError(canary)

    client = AcpStdioClient(
        process, lambda _message: None, lambda *_args: None, lifecycle,
    )

    with pytest.raises(AcpTransportError, match="ACP transport write failed") as captured:
        client.request("session/prompt", {}, timeout=0.1)
    process.stdout.release.set()

    assert lifecycle_errors == ["ACP transport write failed"]
    assert canary not in str(captured.value)


def test_lone_surrogate_rejects_only_current_inbound_request():
    process = _Process()
    handled, completed = [], Event()

    def handler(client, message):
        handled.append(message["id"])
        client.respond(message["id"], {"ok": True})
        completed.set()

    client = AcpStdioClient(process, lambda _message: None, handler)
    request = {"jsonrpc": "2.0", "method": "_bolt/model.complete"}
    client._receive_request({**request, "id": 92, "params": {"text": "\ud800"}})
    client._receive_request({**request, "id": 93, "params": {"text": "valid"}})
    assert completed.wait(1)
    process.stdout.release.set()

    responses = [json.loads(line) for line in process.stdin.writes]
    assert responses[0]["error"] == {"code": -32602, "message": "Invalid params"}
    assert responses[1]["result"] == {"ok": True}
    assert handled == [93]
    assert client._failure is None
