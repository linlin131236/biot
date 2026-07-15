import json
import os
import re
import urllib.request
from dataclasses import dataclass
from typing import Callable

from bolt_core.tool_operations import operation_for_tool
from bolt_core.workspace_credential_gate import (
    CredentialGateError,
    CredentialLease,
    LockedWorkspace,
    WorkspaceCredentialGate,
)


@dataclass(frozen=True)
class ModelConfig:
    provider: str
    base_url: str
    credential_id: str | None
    model: str
    temperature: float = 0.2
    timeout: float = 120.0
    context_window: int = 8192


@dataclass(frozen=True)
class ModelMessage:
    role: str
    content: str
    tool_call_id: str | None = None
    tool_calls: list[dict] | None = None


@dataclass(frozen=True)
class TokenUsage:
    input_tokens: int
    output_tokens: int
    total_tokens: int


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    arguments: dict


@dataclass(frozen=True)
class ModelRequest:
    messages: list[ModelMessage]
    config: ModelConfig
    locked_workspace: LockedWorkspace | None = None


@dataclass(frozen=True)
class ModelResponse:
    status: str
    content: str | None
    usage: TokenUsage
    tool_calls: list[ToolCall]
    error: str | None = None


class FakeModelGateway:
    """Gateway for testing. Returns tool_calls format matching OpenAI response shape."""

    def complete(self, request: ModelRequest) -> ModelResponse:
        prompt = "\n".join(message.content for message in request.messages)
        call = _fake_tool_call(prompt)
        content = json.dumps({"tool": call.name, "operation": operation_for_tool(call.name), "payload": call.arguments})
        usage = TokenUsage(_count_tokens(prompt), _count_tokens(content), _count_tokens(prompt + content))
        return ModelResponse("completed", content, usage, [call], None)


class OpenAICompatibleGateway:
    """Real OpenAI-compatible gateway with function calling, retry, and timeout."""

    MAX_RETRIES = 3

    def __init__(self, client_factory: Callable | None = None) -> None:
        self._client_factory = client_factory

    def complete(
        self,
        request: ModelRequest,
        lease: CredentialLease | None = None,
        validate: Callable[[], None] | None = None,
    ) -> ModelResponse:
        if lease is None:
            return _failed_response("api key missing")
        try:
            if validate is not None:
                validate()
            return self._complete_with_retry(request, lease.secret)
        except CredentialGateError as error:
            return _failed_response(str(error))

    def _complete_with_retry(self, request: ModelRequest, secret: str) -> ModelResponse:
        from bolt_core.tool_schemas import all_tool_schemas

        try:
            from openai import APIConnectionError, APITimeoutError, RateLimitError, OpenAI
        except ImportError:
            return ModelResponse("failed", None, TokenUsage(0, 0, 0), [], "openai package not installed")

        factory = self._client_factory or OpenAI
        client = factory(base_url=request.config.base_url, api_key=secret, timeout=request.config.timeout)
        messages = [_message_to_openai_dict(msg) for msg in request.messages]
        tools = all_tool_schemas()

        last_error: str | None = None
        for attempt in range(self.MAX_RETRIES):
            try:
                response = client.chat.completions.create(
                    model=request.config.model,
                    temperature=request.config.temperature,
                    messages=messages,
                    tools=tools,
                    tool_choice="auto",
                )
                return _parse_openai_response(response)
            except RateLimitError:
                last_error = "rate limited"
            except APIConnectionError:
                last_error = "connection error"
            except APITimeoutError:
                last_error = "request timed out"
            except Exception as exc:
                last_error = str(exc)
                break
        return ModelResponse("failed", None, TokenUsage(0, 0, 0), [], last_error or "unknown error")


class DefaultModelGateway:
    """Routes explicit fake configs to tests, all real providers to OpenAI-compatible chat."""

    def __init__(
        self,
        fake: FakeModelGateway | None = None,
        real: OpenAICompatibleGateway | None = None,
        credential_gate: WorkspaceCredentialGate | None = None,
    ) -> None:
        self._fake = fake or FakeModelGateway()
        self._real = real or OpenAICompatibleGateway()
        self._credential_gate = credential_gate

    def complete(self, request: ModelRequest) -> ModelResponse:
        if self._credential_gate is not None:
            return self._complete_with_gate(request)
        if request.config.provider == "fake":
            return self._fake.complete(request)
        return self._real.complete(request)

    def _complete_with_gate(self, request: ModelRequest) -> ModelResponse:
        workspace = request.locked_workspace
        if workspace is None:
            return _failed_response("credential_workspace_required")
        try:
            lease = self._credential_gate.resolve(workspace, request.config.provider)
        except CredentialGateError as error:
            return _failed_response(str(error))
        validate = lambda: self._credential_gate.validate(workspace, request.config.provider, lease)
        if request.config.provider == "fake":
            try:
                validate()
            except CredentialGateError as error:
                return _failed_response(str(error))
            return self._fake.complete(request)
        return self._real.complete(request, lease, validate)


def _failed_response(error: str) -> ModelResponse:
    return ModelResponse("failed", None, TokenUsage(0, 0, 0), [], error)


def _fake_tool_call(prompt: str) -> ToolCall:
    workspace = _fake_workspace(prompt)
    normalized = prompt.lower()
    if "read" in normalized:
        return ToolCall("call_fake_read", "file.read", {"path": f"{workspace}/README.md"})
    if "write" in normalized:
        return ToolCall("call_fake_write", "file.write", {"path": f"{workspace}/README.md", "proposed_content": "# Bolt\n"})
    if "shell" in normalized or "test" in normalized:
        return ToolCall("call_fake_shell", "shell.execute", {"command": "python --version", "workdir": workspace})
    return ToolCall("call_fake_default", "file.read", {"path": f"{workspace}/README.md"})


def _fake_workspace(prompt: str) -> str:
    match = re.search(r"root_path['\"]?: ['\"]([^'\"]+)['\"]", prompt)
    return match.group(1).replace("\\", "/") if match else "."


def _parse_openai_response(response) -> ModelResponse:
    choice = response.choices[0]
    message = choice.message
    content = message.content or ""
    raw_usage = getattr(response, "usage", None) or None
    if raw_usage:
        usage = TokenUsage(raw_usage.prompt_tokens, raw_usage.completion_tokens, raw_usage.total_tokens)
    else:
        usage = TokenUsage(0, 0, 0)
    tool_calls = []
    if message.tool_calls:
        for tc in message.tool_calls:
            try:
                args = json.loads(tc.function.arguments)
            except json.JSONDecodeError:
                args = {}
            tool_calls.append(ToolCall(tc.id, tc.function.name, args))
    return ModelResponse("completed", content, usage, tool_calls, None)


def _message_to_openai_dict(message: ModelMessage) -> dict:
    data: dict = {"role": message.role, "content": message.content}
    if message.role == "tool" and message.tool_call_id:
        data["tool_call_id"] = message.tool_call_id
    if message.tool_calls:
        data["tool_calls"] = message.tool_calls
    return data


def _count_tokens(text: str) -> int:
    return max(1, len(text.split()))
