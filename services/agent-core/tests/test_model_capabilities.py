import pytest

from bolt_core.model_capabilities import ModelCapabilities


FULL_CAPABILITIES = {
    "tool_calling": True,
    "parallel_tools": False,
    "reasoning": True,
    "images": False,
    "prompt_cache": True,
    "context_window": 128000,
    "max_output_tokens": 16384,
}


def test_model_capabilities_requires_a_complete_declaration():
    declaration = dict(FULL_CAPABILITIES)
    declaration.pop("images")

    with pytest.raises(ValueError, match="capability_declaration_incomplete"):
        ModelCapabilities.from_declaration(declaration)


def test_tool_calling_profile_allows_auto_coding():
    capabilities = ModelCapabilities.from_declaration(FULL_CAPABILITIES)

    capabilities.allow_mode("auto_coding")


def test_profile_without_tool_calling_rejects_auto_coding():
    declaration = {**FULL_CAPABILITIES, "tool_calling": False}
    capabilities = ModelCapabilities.from_declaration(declaration)

    with pytest.raises(ValueError, match="tool_calling_required_for_auto_coding"):
        capabilities.allow_mode("auto_coding")


def test_profile_without_tool_calling_allows_question_answer():
    declaration = {**FULL_CAPABILITIES, "tool_calling": False}
    capabilities = ModelCapabilities.from_declaration(declaration)

    capabilities.allow_mode("question_answer")


def test_model_capabilities_rejects_unknown_declaration_field():
    declaration = {**FULL_CAPABILITIES, "experimental": True}

    with pytest.raises(ValueError, match="capability_declaration_unknown"):
        ModelCapabilities.from_declaration(declaration)


def test_model_capabilities_rejects_non_mapping_declaration():
    with pytest.raises(ValueError, match="capability_declaration_invalid"):
        ModelCapabilities.from_declaration([])


def test_model_capabilities_rejects_runtime_overrides():
    with pytest.raises(ValueError, match="runtime_capability_overrides_not_allowed"):
        ModelCapabilities.from_declaration(FULL_CAPABILITIES, runtime_overrides={"images": True})


def test_model_capabilities_rejects_parallel_tools_without_tool_calling():
    declaration = {**FULL_CAPABILITIES, "tool_calling": False, "parallel_tools": True}

    with pytest.raises(ValueError, match="capability_declaration_invalid"):
        ModelCapabilities.from_declaration(declaration)
