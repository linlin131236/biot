import json
import sys

session_id = "hermes-session"
for raw in sys.stdin:
    request = json.loads(raw)
    method = request.get("method")
    params = request.get("params", {})
    request_id = request.get("id")
    if method == "initialize":
        result = {
            "protocolVersion": 1,
            "agentInfo": {"name": "hermes-agent", "version": "0.24.0"},
            "agentCapabilities": {"loadSession": True, "promptCapabilities": {"image": True}},
        }
    elif method == "session/new":
        if not isinstance(params.get("mcpServers"), list):
            print(json.dumps({
                "jsonrpc": "2.0", "id": request_id,
                "error": {"code": -32602, "message": "mcpServers is required"},
            }), flush=True)
            continue
        result = {"sessionId": session_id}
    elif method == "session/load":
        result = {} if params.get("sessionId") == session_id else None
    elif method == "session/prompt":
        text = params["prompt"][0]["text"]
        if text == "request permission":
            permission_id = "permission_123"
            print(json.dumps({
                "jsonrpc": "2.0",
                "id": 101,
                "method": "session/request_permission",
                "params": {
                    "sessionId": session_id,
                    "toolCall": {
                        "toolCallId": permission_id,
                        "title": "Run read-only command",
                        "kind": "execute",
                        "status": "pending",
                    },
                    "options": [
                        {"optionId": "allow_once", "name": "Allow once", "kind": "allow_once"},
                        {"optionId": "deny", "name": "Deny", "kind": "reject_once"},
                    ],
                },
            }), flush=True)
            permission_response = json.loads(sys.stdin.readline())
            outcome = permission_response.get("result", {}).get("outcome", {})
            selected = outcome.get("optionId") if outcome.get("outcome") == "selected" else "denied"
            print(json.dumps({
                "jsonrpc": "2.0",
                "method": "session/update",
                "params": {
                    "sessionId": session_id,
                    "update": {
                        "sessionUpdate": "agent_message_chunk",
                        "content": {"type": "text", "text": f"permission {selected}"},
                    },
                },
            }), flush=True)
        else:
            print(json.dumps({
                "jsonrpc": "2.0",
                "method": "session/update",
                "params": {
                    "sessionId": session_id,
                    "update": {
                        "sessionUpdate": "agent_message_chunk",
                        "content": {"type": "text", "text": "hello from fake Hermes"},
                    },
                },
            }), flush=True)
        result = {"stopReason": "end_turn", "usage": {"inputTokens": 2, "outputTokens": 3, "totalTokens": 5}}
    elif method == "session/cancel":
        result = None
    else:
        print(json.dumps({"jsonrpc": "2.0", "id": request_id, "error": {"code": -32601, "message": "unknown method"}}), flush=True)
        continue
    if request_id is not None:
        print(json.dumps({"jsonrpc": "2.0", "id": request_id, "result": result}), flush=True)
