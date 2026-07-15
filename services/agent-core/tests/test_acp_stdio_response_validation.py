from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from bolt_core.runtime.acp_stdio import AcpStdioClient


def test_malformed_response_cannot_complete_pending_request(tmp_path: Path):
    script = tmp_path / "malformed_response_child.py"
    script.write_text(
        """
import json, sys
request = json.loads(sys.stdin.readline())
request_id = request["id"]
malformed = [
 {"id": request_id},
 {"jsonrpc": "1.0", "id": request_id, "result": {"bad": 1}},
 {"jsonrpc": "2.0", "id": str(request_id), "result": {"bad": 2}},
 {"jsonrpc": "2.0", "id": request_id, "result": {}, "error": {}},
]
for response in malformed:
 print(json.dumps(response), flush=True)
print(json.dumps({"jsonrpc":"2.0","id":request_id,"result":{"ok":True}}), flush=True)
""",
        encoding="utf-8",
    )
    process = subprocess.Popen(
        [sys.executable, "-u", str(script)], stdin=subprocess.PIPE,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    client = AcpStdioClient(process, lambda _message: None, lambda *_args: None)
    try:
        assert client.request("session/prompt", {}) == {"ok": True}
    finally:
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=2)
