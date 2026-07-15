"""Static model capability declarations and execution-mode checks."""

from dataclasses import dataclass
from typing import Mapping


QUESTION_ANSWER = "question_answer"
AUTO_CODING = "auto_coding"
_BOOLEAN_CAPABILITIES = (
    "tool_calling",
    "parallel_tools",
    "reasoning",
    "images",
    "prompt_cache",
)
_CAPABILITY_FIELDS = (*_BOOLEAN_CAPABILITIES, "context_window", "max_output_tokens")


@dataclass(frozen=True)
class ModelCapabilities:
    tool_calling: bool
    parallel_tools: bool
    reasoning: bool
    images: bool
    prompt_cache: bool
    context_window: int
    max_output_tokens: int

    @classmethod
    def from_declaration(
        cls,
        declaration: Mapping[str, object],
        *,
        runtime_overrides: Mapping[str, object] | None = None,
    ) -> "ModelCapabilities":
        if not isinstance(declaration, Mapping):
            raise ValueError("capability_declaration_invalid")
        if runtime_overrides is not None:
            raise ValueError("runtime_capability_overrides_not_allowed")
        _validate_fields(declaration)
        _validate_values(declaration)
        return cls(**declaration)

    def allow_mode(self, mode: str) -> None:
        if mode == QUESTION_ANSWER:
            return
        if mode == AUTO_CODING:
            if self.tool_calling:
                return
            raise ValueError("tool_calling_required_for_auto_coding")
        raise ValueError("model_mode_not_supported")


def _validate_fields(declaration: Mapping[str, object]) -> None:
    names = set(declaration)
    expected = set(_CAPABILITY_FIELDS)
    if names - expected:
        raise ValueError("capability_declaration_unknown")
    if expected - names:
        raise ValueError("capability_declaration_incomplete")


def _validate_values(declaration: Mapping[str, object]) -> None:
    if any(type(declaration[name]) is not bool for name in _BOOLEAN_CAPABILITIES):
        raise ValueError("capability_declaration_invalid")
    if declaration["parallel_tools"] and not declaration["tool_calling"]:
        raise ValueError("capability_declaration_invalid")
    for name in ("context_window", "max_output_tokens"):
        if type(declaration[name]) is not int or declaration[name] < 1:
            raise ValueError("capability_declaration_invalid")
