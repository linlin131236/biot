from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from threading import Event, Thread
from time import monotonic, sleep

import pytest

from bolt_core.runtime.acp_stdio import AcpStdioClient, AcpTransportError


def _spawn(tmp_path: Path, source: str, handler, notifications=None, lifecycle=None):
    script = tmp_path / "acp_child.py"
    script.write_text(source, encoding="utf-8")
    process = subprocess.Popen(
        [sys.executable, "-u", str(script)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    client = AcpStdioClient(
        process,
        (notifications if notifications is not None else []).append,
        handler,
        (lifecycle if lifecycle is not None else []).append,
    )
    return client, process


def _stop(process: subprocess.Popen) -> None:
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=2)


def _wait(event: Event, timeout: float = 3) -> None:
    assert event.wait(timeout), "ACP child did not finish its protocol exchange"


def test_runtime_request_round_trip_does_not_collide_with_core_request_id(tmp_path):
    source = """
import json, sys
core_request = json.loads(sys.stdin.readline())
reverse = {
    "jsonrpc": "2.0", "id": core_request["id"],
    "method": "_bolt/model.complete",
    "params": {"sessionId": "external-session", "payload": {"messages": []}},
}
print(json.dumps(reverse), flush=True)
bridge_response = json.loads(sys.stdin.readline())
print(json.dumps({
    "jsonrpc": "2.0", "id": core_request["id"],
    "result": {"bridge": bridge_response["result"]},
}), flush=True)
"""

    def handle(client, message):
        client.respond(message["id"], {"content": "MODEL_OK"})

    client, process = _spawn(tmp_path, source, handle)
    try:
        result = client.request("session/prompt", {"text": "hello"})
        assert result == {"bridge": {"content": "MODEL_OK"}}
    finally:
        _stop(process)


def test_invalid_runtime_requests_are_rejected_before_the_handler(tmp_path):
    source = """
import json, sys
requests = [
    {"jsonrpc": "2.0", "id": "bad-id", "method": "_bolt/model.complete", "params": {}},
    {"jsonrpc": "2.0", "id": 2, "method": "bolt/unknown", "params": {}},
    {"jsonrpc": "2.0", "id": 3, "method": "_bolt/model.complete"},
    {"jsonrpc": "2.0", "id": 4, "method": "_bolt/model.complete", "params": []},
    {"jsonrpc": "2.0", "id": 5, "method": "_bolt/model.complete", "params": {"blob": "x" * 300000}},
]
responses = []
for request in requests:
    print(json.dumps(request), flush=True)
    responses.append(json.loads(sys.stdin.readline()))
print(json.dumps({"jsonrpc": "2.0", "method": "test/done", "params": responses}), flush=True)
"""
    notifications: list[dict] = []
    done = Event()

    def on_notification(message):
        notifications.append(message)
        done.set()

    def unexpected_handler(_client, _message):
        raise AssertionError("invalid request reached handler")

    client, process = _spawn(tmp_path, source, unexpected_handler, notifications=[])
    client._notification_handler = on_notification
    try:
        _wait(done)
        responses = notifications[0]["params"]
        assert [(item.get("id"), item["error"]["code"]) for item in responses] == [
            (None, -32600), (2, -32601), (3, -32602), (4, -32602), (5, -32602),
        ]
        encoded = json.dumps(responses)
        assert "bad-id" not in encoded
        assert "xxxxxxxx" not in encoded
    finally:
        _stop(process)


def test_handler_exception_returns_generic_error_and_reader_survives(tmp_path):
    canary = "prompt-canary-must-not-escape"
    source = f"""
import json, sys
print({canary!r}, file=sys.stderr, flush=True)
print(json.dumps({{
    "jsonrpc": "2.0", "id": 9, "method": "_bolt/model.complete",
    "params": {{"sessionId": "external-session", "payload": {{"prompt": {canary!r}}}}},
}}), flush=True)
response = json.loads(sys.stdin.readline())
print(json.dumps({{"jsonrpc": "2.0", "method": "test/done", "params": response}}), flush=True)
"""
    notifications: list[dict] = []
    done = Event()
    lifecycle: list[Exception] = []

    def on_notification(message):
        notifications.append(message)
        done.set()

    def fail_handler(_client, _message):
        raise RuntimeError(canary)

    client, process = _spawn(tmp_path, source, fail_handler, notifications=[], lifecycle=lifecycle)
    client._notification_handler = on_notification
    try:
        _wait(done)
        response = notifications[0]["params"]
        assert response == {
            "jsonrpc": "2.0", "id": 9,
            "error": {"code": -32603, "message": "Internal error"},
        }
        assert canary not in json.dumps(response)
        assert all(canary not in str(error) for error in lifecycle)
    finally:
        _stop(process)


def test_oversized_transport_message_fails_closed_without_handler_input(tmp_path):
    source = """
import json
print(json.dumps({
    "jsonrpc": "2.0", "id": 7, "method": "_bolt/model.complete",
    "params": {"blob": "z" * 1100000},
}), flush=True)
"""
    lifecycle: list[Exception] = []
    called = Event()
    client, process = _spawn(
        tmp_path, source, lambda _client, _message: called.set(), lifecycle=lifecycle,
    )
    try:
        deadline = monotonic() + 3
        while not lifecycle and monotonic() < deadline:
            sleep(0.01)
        assert lifecycle
        assert str(lifecycle[0]) == "ACP transport message exceeded limit"
        assert not called.is_set()
    finally:
        _stop(process)


@pytest.mark.parametrize("mode", ["eof", "crash"])
def test_pending_request_wakes_immediately_on_eof_or_crash(tmp_path, mode):
    exit_code = 0 if mode == "eof" else 17
    source = f"""
import sys
sys.stdin.readline()
raise SystemExit({exit_code})
"""
    client, process = _spawn(tmp_path, source, lambda *_args: None)
    started = monotonic()
    try:
        with pytest.raises(AcpTransportError, match="ACP transport closed"):
            client.request("session/prompt", {"text": "wait"}, timeout=10)
        assert monotonic() - started < 3
    finally:
        _stop(process)


def test_close_wakes_pending_once_and_late_response_cannot_block_reader(tmp_path):
    source = """
import json, sys, time
request = json.loads(sys.stdin.readline())
time.sleep(0.2)
print(json.dumps({"jsonrpc": "2.0", "id": request["id"], "result": {"late": True}}), flush=True)
print(json.dumps({"jsonrpc": "2.0", "method": "test/after-late", "params": {}}), flush=True)
time.sleep(2)
"""
    notifications: list[dict] = []
    noticed = Event()

    def on_notification(message):
        notifications.append(message)
        noticed.set()

    client, process = _spawn(tmp_path, source, lambda *_args: None, notifications=[])
    client._notification_handler = on_notification
    outcomes: list[object] = []

    def request():
        try:
            outcomes.append(client.request("session/prompt", {"text": "cancel"}, timeout=5))
        except Exception as error:
            outcomes.append(error)

    thread = Thread(target=request)
    thread.start()
    try:
        deadline = monotonic() + 2
        while not client._responses and monotonic() < deadline:
            sleep(0.01)
        client.close()
        thread.join(timeout=2)
        assert not thread.is_alive()
        assert len(outcomes) == 1
        assert isinstance(outcomes[0], AcpTransportError)
        _wait(noticed)
        assert notifications[0]["method"] == "test/after-late"
    finally:
        _stop(process)


def test_broken_pipe_fails_request_without_leaking_payload():
    canary = "authorization-canary-must-not-escape"

    class BrokenInput:
        def write(self, _value):
            raise BrokenPipeError(canary)

        def flush(self):
            raise AssertionError("flush must not run")

    class EmptyOutput:
        def readline(self, _limit=-1):
            sleep(0.05)
            return b""

    class Process:
        stdin = BrokenInput()
        stdout = EmptyOutput()
        stderr = None

        @staticmethod
        def poll():
            return 19

    lifecycle: list[Exception] = []
    client = AcpStdioClient(Process(), lambda _message: None, lambda *_args: None, lifecycle.append)

    with pytest.raises(AcpTransportError, match="ACP transport write failed") as captured:
        client.request("session/prompt", {"text": canary})

    assert canary not in str(captured.value)
    deadline = monotonic() + 1
    while not lifecycle and monotonic() < deadline:
        sleep(0.01)
    assert lifecycle
    assert all(canary not in str(error) for error in lifecycle)
