"""Tests for evidence_redactor — conservative secret redaction."""
import pytest

from bolt_core.evidence_redactor import redact


def test_redact_openai_api_key():
    assert redact("OPENAI_API_KEY=sk-abc123") == "OPENAI_API_KEY=[已脱敏]"


def test_redact_api_key():
    assert redact("API_KEY=secret123") == "API_KEY=[已脱敏]"


def test_redact_token():
    assert redact("TOKEN=ghp_abc123") == "TOKEN=[已脱敏]"


def test_redact_secret():
    assert redact("SECRET=mysecret") == "SECRET=[已脱敏]"


def test_redact_password():
    assert redact("PASSWORD=admin123") == "PASSWORD=[已脱敏]"


def test_redact_bearer_token():
    assert redact("Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.xxx") == "Authorization: Bearer [已脱敏]"


def test_redact_sk_prefix_key():
    assert redact("sk-proj-abc123def456789") == "sk-[已脱敏]"


def test_redact_private_key():
    assert redact("-----BEGIN PRIVATE KEY-----\nabc\n-----END PRIVATE KEY-----") == "[已脱敏：私钥]"


def test_redact_certificate():
    text = "Certificate:\n-----BEGIN CERTIFICATE-----\nMIID...\n-----END CERTIFICATE-----"
    result = redact(text)
    assert "CERTIFICATE" not in result or "[已脱敏：证书]" in result


def test_preserve_normal_output():
    """非敏感输出保持不变。"""
    assert redact("491 passed, 0 failed") == "491 passed, 0 failed"


def test_preserve_chinese_text():
    """中文文案不被误删。"""
    text = "执行完成：验证命令 pytest 已运行，结果：491 passed"
    assert redact(text) == text


def test_preserve_command_without_secrets():
    """普通命令不脱敏。"""
    assert redact("pnpm test") == "pnpm test"
    assert redact("uv run pytest -q") == "uv run pytest -q"


def test_redact_multiple_secrets():
    """多个敏感值同时脱敏。"""
    text = "API_KEY=abc TOKEN=def sk-proj-abc123def456789"
    result = redact(text)
    assert "API_KEY=[已脱敏]" in result
    assert "TOKEN=[已脱敏]" in result
    assert "sk-[已脱敏]" in result


def test_redact_key_value_with_spaces():
    """带空格的 key=value 格式脱敏。"""
    assert redact("export OPENAI_API_KEY = sk-abc") == "export OPENAI_API_KEY=[已脱敏]"


def test_empty_string():
    assert redact("") == ""


def test_no_false_positive_on_partial_match():
    """部分匹配不误脱敏。"""
    assert redact("apikey = test") == "apikey = test"
    assert redact("MY_TOKENIZER_CONFIG") == "MY_TOKENIZER_CONFIG"
