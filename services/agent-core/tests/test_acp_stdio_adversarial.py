from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from threading import Event
from time import monotonic, sleep

from bolt_core.runtime.acp_stdio import AcpStdioClient, AcpTransportError


def _spawn(tmp_path: Path, source: str, handler, notifications=None, lifecycle=None):
    script = tmp_path / "adversarial_child.py"
    script.write_text(source, encoding="utf-8")
    process = subprocess.Popen(
        [sys.executable, "-u", str(script)], stdin=subprocess.PIPE,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
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


def _wait_for(predicate, timeout: float = 3) -> None:
    deadline = monotonic() + timeout
    while not predicate() and monotonic() < deadline:
        sleep(0.01)
    assert predicate()


def test_duplicate_active_id_runs_one_handler_and_one_terminal_response(tmp_path):
    source = """
import json, time
response = json.loads(input())
print(json.dumps({"jsonrpc":"2.0","method":"test/done","params":response}), flush=True)
time.sleep(1)
"""
    release, started, notifications = Event(), [], []
    client, process = _spawn(
        tmp_path, source, lambda *_args: None, notifications=notifications,
    )

    def handler(active_client, message):
        started.append(message["id"])
        release.wait(2)
        active_client.respond(message["id"], {"ok": True})

    client._request_handler = handler
    request = {"jsonrpc": "2.0", "id": 41, "method": "_bolt/model.complete", "params": {}}
    try:
        client._receive_request(request)
        _wait_for(lambda: started == [41])
        client._receive_request(request)
        release.set()
        _wait_for(lambda: bool(notifications))
        assert started == [41]
        assert notifications[0]["params"] == {
            "jsonrpc": "2.0", "id": 41, "result": {"ok": True},
        }
    finally:
        _stop(process)


def test_inbound_capacity_is_bounded_and_released_after_handlers_return(tmp_path):
    source = """
import json, sys, time
for request_id in range(1, 40):
 print(json.dumps({"jsonrpc":"2.0","id":request_id,"method":"_bolt/model.complete","params":{}}), flush=True)
time.sleep(2)
"""
    release = Event()
    started = []

    def handler(_client, message):
        started.append(message["id"])
        release.wait(2)

    client, process = _spawn(tmp_path, source, handler)
    try:
        _wait_for(lambda: len(started) >= 1)
        sleep(0.2)
        assert len(started) <= 8
        assert len(client._inbound_requests) <= 8
        release.set()
        _wait_for(lambda: not client._inbound_requests)
    finally:
        _stop(process)


def test_handler_return_without_response_returns_generic_error(tmp_path):
    source = """
import json, time
request = {"jsonrpc":"2.0","id":5,"method":"_bolt/model.complete","params":{}}
print(json.dumps(request), flush=True)
response = json.loads(input())
print(json.dumps({"jsonrpc":"2.0","method":"test/done","params":response}), flush=True)
time.sleep(1)
"""
    calls = []
    notifications = []
    client, process = _spawn(
        tmp_path, source, lambda _client, message: calls.append(message["id"]),
        notifications=notifications,
    )
    try:
        _wait_for(lambda: bool(notifications))
        assert calls == [5]
        assert notifications[0]["params"]["error"] == {
            "code": -32603, "message": "Internal error",
        }
        assert client._inbound_requests == set()
    finally:
        _stop(process)


def test_close_clears_inbound_pending_and_late_respond_is_rejected(tmp_path):
    source = """
import json, time
print(json.dumps({"jsonrpc":"2.0","id":8,"method":"_bolt/model.complete","params":{}}), flush=True)
time.sleep(2)
"""
    started = Event()
    release = Event()
    outcomes = []

    def handler(client, message):
        started.set()
        release.wait(2)
        try:
            client.respond(message["id"], {"late": True})
        except Exception as error:
            outcomes.append(error)

    client, process = _spawn(tmp_path, source, handler)
    try:
        assert started.wait(2)
        client.close()
        assert client._inbound_requests == set()
        release.set()
        _wait_for(lambda: bool(outcomes))
        assert isinstance(outcomes[0], (AcpTransportError, ValueError))
    finally:
        _stop(process)


def test_inbound_response_broken_pipe_clears_pending_without_leak():
    canary = "runtime-secret-canary"
    request = {
        "jsonrpc": "2.0", "id": 12,
        "method": "_bolt/model.complete", "params": {},
    }

    class BrokenInput:
        def write(self, _value):
            raise BrokenPipeError(canary)

        def flush(self):
            raise AssertionError("flush must not run")

    class OneMessageOutput:
        def __init__(self):
            self._message = (json.dumps(request) + "\n").encode()

        def readline(self, _limit=-1):
            if self._message:
                message, self._message = self._message, b""
                return message
            sleep(0.1)
            return b""

    class Process:
        stdin = BrokenInput()
        stdout = OneMessageOutput()
        stderr = None

        @staticmethod
        def poll():
            return 19

    outcomes = []
    lifecycle = []

    def handler(client, message):
        try:
            client.respond(message["id"], {"value": canary})
        except Exception as error:
            outcomes.append(error)

    client = AcpStdioClient(Process(), lambda _message: None, handler, lifecycle.append)
    _wait_for(lambda: bool(outcomes))
    _wait_for(lambda: bool(lifecycle))
    assert isinstance(outcomes[0], AcpTransportError)
    assert str(outcomes[0]) == "ACP transport write failed"
    assert canary not in str(outcomes[0])
    assert client._inbound_requests == set()
    assert len(lifecycle) == 1


def test_malformed_json_is_ignored_and_next_notification_survives(tmp_path):
    source = """
import json, time
print('{bad json', flush=True)
print(json.dumps({"jsonrpc":"2.0","method":"test/alive","params":{}}), flush=True)
time.sleep(1)
"""
    notifications = []
    client, process = _spawn(tmp_path, source, lambda *_args: None, notifications=notifications)
    try:
        _wait_for(lambda: bool(notifications))
        assert notifications[0]["method"] == "test/alive"
    finally:
        _stop(process)


def test_notification_handler_exception_fails_transport_with_generic_error(tmp_path):
    canary = "authorization-canary-do-not-leak"
    source = f"""
import json, time
print(json.dumps({{"jsonrpc":"2.0","method":"test/bad","params":{{"value":{canary!r}}}}}), flush=True)
time.sleep(1)
"""
    lifecycle = []

    def fail_notification(_message):
        raise RuntimeError(canary)

    client, process = _spawn(
        tmp_path, source, lambda *_args: None,
        notifications=[], lifecycle=lifecycle,
    )
    client._notification_handler = fail_notification
    try:
        _wait_for(lambda: bool(lifecycle))
        assert str(lifecycle[0]) == "ACP transport read failed"
        assert canary not in str(lifecycle[0])
    finally:
        _stop(process)
