import json
import urllib.request
from dataclasses import dataclass


@dataclass(frozen=True)
class ModelConfig:
    provider: str
    base_url: str
    api_key: str | None
    model: str
    temperature: float = 0.2


@dataclass(frozen=True)
class ModelMessage:
    role: str
    content: str


@dataclass(frozen=True)
class TokenUsage:
    input_tokens: int
    output_tokens: int
    total_tokens: int


@dataclass(frozen=True)
class ModelRequest:
    messages: list[ModelMessage]
    config: ModelConfig


@dataclass(frozen=True)
class ModelResponse:
    status: str
    content: str
    usage: TokenUsage
    error: str | None = None


class FakeModelGateway:
    def complete(self, request: ModelRequest) -> ModelResponse:
        prompt = "\n".join(message.content for message in request.messages).lower()
        content = _fake_tool_request(prompt)
        usage = TokenUsage(_count_tokens(prompt), _count_tokens(content), _count_tokens(prompt + content))
        return ModelResponse("completed", content, usage, None)


class OpenAICompatibleGateway:
    def complete(self, request: ModelRequest) -> ModelResponse:
        if not request.config.api_key:
            return ModelResponse("failed", "", TokenUsage(0, 0, 0), "api key missing")
        payload = _request_payload(request)
        raw = self._post(request.config, payload)
        return _parse_openai_response(raw)

    def _post(self, config: ModelConfig, payload: dict) -> bytes:
        data = json.dumps(payload).encode("utf-8")
        url = config.base_url.rstrip("/") + "/chat/completions"
        req = urllib.request.Request(url, data=data, headers=_headers(config), method="POST")
        with urllib.request.urlopen(req, timeout=60) as response:
            return response.read()


def _fake_tool_request(prompt: str) -> str:
    if "write" in prompt or "改" in prompt:
        return json.dumps({"tool": "file.write", "operation": "write", "payload": {"path": "D:/Bolt/Bolt/README.md", "proposed_content": "# Bolt\n"}})
    if "shell" in prompt or "test" in prompt or "测试" in prompt:
        return json.dumps({"tool": "shell.execute", "operation": "command", "payload": {"command": "python --version", "workdir": "D:/Bolt/Bolt"}})
    return json.dumps({"tool": "file.read", "operation": "read", "payload": {"path": "D:/Bolt/Bolt/README.md"}})


def _request_payload(request: ModelRequest) -> dict:
    return {
        "model": request.config.model,
        "temperature": request.config.temperature,
        "messages": [message.__dict__ for message in request.messages],
    }


def _parse_openai_response(raw: bytes) -> ModelResponse:
    payload = json.loads(raw.decode("utf-8"))
    content = payload["choices"][0]["message"]["content"]
    usage = payload.get("usage", {})
    tokens = TokenUsage(usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0), usage.get("total_tokens", 0))
    return ModelResponse("completed", content, tokens, None)


def _headers(config: ModelConfig) -> dict[str, str]:
    return {"authorization": f"Bearer {config.api_key}", "content-type": "application/json"}


def _count_tokens(text: str) -> int:
    return max(1, len(text.split()))
