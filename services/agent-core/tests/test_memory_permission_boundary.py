"""Tests for MemoryPermissionBoundary."""
import pytest

from bolt_core.memory_permission_boundary import (
    MemoryPermissionBoundary,
    PermissionDecision,
    PermissionTier,
    _TIER_LABELS,
    _TIER_READABLE,
    _TIER_WRITABLE,
    _TIER_DISPLAYABLE,
)


# ── PermissionDecision ─────────────────────────────────────────────────

def test_permission_decision_fields():
    d = PermissionDecision(
        tier=PermissionTier.SECRET,
        tier_label="机密信息",
        can_read=False,
        can_write=False,
        can_display=False,
        explanation_cn="检测到机密",
        redacted_content="[已脱敏]",
        detected_patterns=["OpenAI API Key"],
    )
    dd = d.to_dict()
    assert dd["tier"] == "secret"
    assert dd["can_read"] is False
    assert dd["can_write"] is False
    assert dd["can_display"] is False
    assert dd["explanation_cn"] == "检测到机密"


def test_permission_decision_is_frozen():
    d = PermissionDecision(
        tier=PermissionTier.PUBLIC_PROJECT,
        tier_label="公开",
        can_read=True,
        can_write=False,
        can_display=True,
        explanation_cn="公开信息",
        redacted_content=None,
        detected_patterns=[],
    )
    with pytest.raises(Exception):
        d.tier = PermissionTier.SECRET  # type: ignore[misc]


# ── Boundary: secret detection ─────────────────────────────────────────

def test_classify_detects_openai_key():
    boundary = MemoryPermissionBoundary()
    decision = boundary.classify("sk-abc123def456ghi789jkl012mno345pqr678stu")
    assert decision.tier == PermissionTier.SECRET
    assert decision.can_read is False
    assert decision.can_write is False
    assert "OpenAI" in decision.explanation_cn or "机密" in decision.explanation_cn


def test_classify_detects_aws_key():
    boundary = MemoryPermissionBoundary()
    decision = boundary.classify("AKIA1234567890ABCDEF")
    assert decision.tier == PermissionTier.SECRET


def test_classify_detects_private_key():
    boundary = MemoryPermissionBoundary()
    decision = boundary.classify("-----BEGIN PRIVATE KEY-----\nMIIEvg...")
    assert decision.tier == PermissionTier.SECRET


def test_classify_redacts_secret():
    boundary = MemoryPermissionBoundary()
    decision = boundary.classify("My key is sk-abc123def456ghi789jkl012mno345pqr678stu")
    assert decision.redacted_content is not None
    assert "sk-abc" not in (decision.redacted_content or "")


# ── Boundary: sensitive detection ─────────────────────────────────────

def test_classify_detects_password():
    boundary = MemoryPermissionBoundary()
    decision = boundary.classify("password: mysecret123")
    assert decision.tier == PermissionTier.SENSITIVE
    assert decision.can_read is False
    assert "密码" in decision.explanation_cn


def test_classify_detects_api_key_field():
    boundary = MemoryPermissionBoundary()
    decision = boundary.classify("api_key: abcdefghij1234567890")
    assert decision.tier in (PermissionTier.SENSITIVE, PermissionTier.SECRET)


# ── Boundary: project content ──────────────────────────────────────────

def test_classify_project_internal():
    boundary = MemoryPermissionBoundary()
    decision = boundary.classify("docs/decisions/073-decision-memory.md 的设计决策")
    assert decision.tier in (PermissionTier.PROJECT_INTERNAL, PermissionTier.PUBLIC_PROJECT)
    assert decision.can_read is True


def test_classify_public_project():
    boundary = MemoryPermissionBoundary()
    decision = boundary.classify("Bolt 是一个桌面 AI 编程 Agent")
    assert decision.tier == PermissionTier.PUBLIC_PROJECT
    assert decision.can_read is True
    assert decision.can_display is True


# ── Boundary: user preference ──────────────────────────────────────────

def test_classify_user_preference():
    boundary = MemoryPermissionBoundary()
    decision = boundary.classify("用户偏好：所有 UI 必须中文")
    assert decision.tier == PermissionTier.USER_PREFERENCE
    assert decision.can_read is True


# ── Boundary: unknown ──────────────────────────────────────────────────

def test_classify_unknown():
    boundary = MemoryPermissionBoundary()
    decision = boundary.classify_unknown("some unknown binary content")
    assert decision.tier == PermissionTier.UNKNOWN
    assert decision.can_read is False
    assert decision.can_write is False


# ── Boundary: should_block_memory_write ────────────────────────────────

def test_block_secret_write():
    boundary = MemoryPermissionBoundary()
    blocked, reason = boundary.should_block_memory_write("sk-abc123def456ghi789jkl012")
    assert blocked is True


def test_block_sensitive_write():
    boundary = MemoryPermissionBoundary()
    blocked, reason = boundary.should_block_memory_write("password: secret123")
    assert blocked is True


def test_allow_public_write_without_source():
    boundary = MemoryPermissionBoundary()
    blocked, reason = boundary.should_block_memory_write("Bolt 项目信息")
    assert blocked is False


def test_preference_write_needs_source():
    boundary = MemoryPermissionBoundary()
    blocked, reason = boundary.should_block_memory_write("用户偏好：中文", source="")
    assert blocked is True
    assert "source_refs" in reason


def test_preference_write_with_source():
    boundary = MemoryPermissionBoundary()
    blocked, reason = boundary.should_block_memory_write(
        "用户偏好：中文", source="docs/project-state.md"
    )
    assert blocked is False


# ── Tier coverage ──────────────────────────────────────────────────────

def test_all_tiers_have_labels():
    for tier in PermissionTier:
        assert tier in _TIER_LABELS, f"Missing label for {tier}"
        assert tier in _TIER_READABLE, f"Missing readable for {tier}"
        assert tier in _TIER_WRITABLE, f"Missing writable for {tier}"
        assert tier in _TIER_DISPLAYABLE, f"Missing displayable for {tier}"


def test_secret_tier_blocked():
    assert _TIER_READABLE[PermissionTier.SECRET] is False
    assert _TIER_WRITABLE[PermissionTier.SECRET] is False
    assert _TIER_DISPLAYABLE[PermissionTier.SECRET] is False


def test_unknown_tier_conservative():
    assert _TIER_READABLE[PermissionTier.UNKNOWN] is False
    assert _TIER_WRITABLE[PermissionTier.UNKNOWN] is False


# ── Redaction quality ──────────────────────────────────────────────────

def test_redact_preserves_non_secret_text():
    boundary = MemoryPermissionBoundary()
    original = "这是一段正常的中文描述，包含 API key：sk-abc123def456ghi789jkl012mno345pqr678stu"
    decision = boundary.classify(original)
    redacted = decision.redacted_content or ""
    assert "正常的中文描述" in redacted
    assert "sk-abc" not in redacted
