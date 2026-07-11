"""Field-level validation policies for non-sensitive persistence values."""

from __future__ import annotations

import ipaddress
import json
import math
from pathlib import Path
import re
from typing import Any
import unicodedata
from urllib.parse import unquote, unquote_plus, urlsplit

_MAX_JSON_BYTES = 64 * 1024
_MAX_JSON_DEPTH = 8
_MAX_URL_LENGTH = 4096
_SENSITIVE_KEY_PARTS = (
    "apikey", "authorization", "credential", "password", "privatekey",
    "secret", "cookie", "header",
)
_TOKEN_USAGE_KEYS = {
    "tokencount", "maxtokens", "inputtokens", "outputtokens", "totaltokens",
    "prompttokens", "completiontokens", "cachedinputtokens", "reasoningtokens",
}
_ASSIGNMENT_PATTERN = re.compile(
    r"(?=(?P<key>[\w.-]+)\s*[:=]\s*\S+)", re.I,
)
_AUTH_CREDENTIAL_PATTERN = re.compile(
    r"(?:basic|bearer)\s+(?P<token>\S+)", re.I,
)
_CREDENTIAL_PREFIX = re.compile(
    r"(?:^|[^a-z0-9])(?:sk-[a-z0-9_-]{6,}|"
    r"(?:gh[pousr]_|github_pat_|aiza|xox[baprs]-|akia)[a-z0-9_-]+)",
    re.I,
)
_DNS_LABEL = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", re.I)
_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")
_PROVIDER_SLUG = re.compile(r"[A-Za-z0-9][A-Za-z0-9-]{0,127}")
_BACKUP_REASON = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}")


def validate_workspace_path(value: object) -> str:
    if not isinstance(value, (str, Path)):
        raise ValueError("invalid workspace path")
    text = str(value)
    if not text or _has_control_character(text) or _component_has_forbidden_data(text):
        raise ValueError("invalid workspace path")
    return text


def validate_backup_reason(value: object) -> str:
    if (
        not isinstance(value, str)
        or _BACKUP_REASON.fullmatch(value) is None
        or _contains_structured_secret(value)
    ):
        raise ValueError("invalid backup reason")
    return value


def validate_identifier(value: object) -> str:
    if (
        not isinstance(value, str)
        or _IDENTIFIER.fullmatch(value) is None
        or _has_control_character(value)
        or _contains_structured_secret(value)
    ):
        raise ValueError("invalid identifier")
    return value


def validate_provider_slug(value: object) -> str:
    if (
        not isinstance(value, str)
        or _PROVIDER_SLUG.fullmatch(value) is None
        or _contains_structured_secret(value)
    ):
        raise ValueError("invalid provider")
    return value


def validate_message_content(value: object) -> str:
    if not isinstance(value, str) or _contains_structured_secret(value):
        raise ValueError("message content contains forbidden sensitive value")
    return value


def validate_credential_reference(value: object) -> str | None:
    if value is None:
        return None
    if (
        not isinstance(value, str)
        or not value
        or _IDENTIFIER.fullmatch(value) is None
        or _has_control_character(value)
        or _contains_structured_secret(value, conservative_auth=True)
    ):
        raise ValueError("invalid credential reference")
    return value


def validate_json_object(value: object) -> str:
    if not isinstance(value, dict):
        raise ValueError("JSON payload must be an object")
    _validate_value(value, depth=0)
    encoded = json.dumps(
        value, allow_nan=False, ensure_ascii=True, separators=(",", ":"), sort_keys=True,
    )
    if len(encoded.encode("utf-8")) > _MAX_JSON_BYTES:
        raise ValueError("JSON payload exceeds size limit")
    return encoded


def validate_http_url(value: object) -> str:
    if not isinstance(value, str) or not _is_bounded_url_text(value):
        raise ValueError("invalid HTTP URL")
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError:
        raise ValueError("invalid HTTP URL") from None
    if not _has_valid_url_structure(value, parsed, port):
        raise ValueError("invalid HTTP URL")
    if (
        not _is_valid_host(parsed.hostname)
        or _component_has_forbidden_data(parsed.hostname)
        or _component_has_forbidden_data(parsed.path)
        or _query_has_forbidden_data(parsed.query)
    ):
        raise ValueError("invalid HTTP URL")
    return value


def _validate_value(value: Any, depth: int) -> None:
    if depth > _MAX_JSON_DEPTH:
        raise ValueError("JSON payload exceeds depth limit")
    if isinstance(value, dict):
        for key, nested in value.items():
            if not isinstance(key, str) or _is_sensitive_key(key):
                raise ValueError("JSON payload contains forbidden sensitive field")
            _validate_value(nested, depth + 1)
    elif isinstance(value, list):
        for nested in value:
            _validate_value(nested, depth + 1)
    elif isinstance(value, str):
        if _contains_structured_secret(value):
            raise ValueError("JSON payload contains forbidden sensitive value")
    elif isinstance(value, float) and not math.isfinite(value):
        raise ValueError("JSON payload contains non-finite number")
    elif not isinstance(value, (int, float, bool, type(None))):
        raise ValueError("JSON payload contains unsupported value")


def _normalize_key(key: str) -> str:
    normalized = unicodedata.normalize("NFKC", key).casefold()
    return "".join(character for character in normalized if character.isalnum())


def _is_sensitive_key(key: str) -> bool:
    normalized = _normalize_key(key)
    if normalized in _TOKEN_USAGE_KEYS:
        return False
    return "token" in normalized or any(
        part in normalized for part in _SENSITIVE_KEY_PARTS
    )


def _contains_structured_secret(
    value: str, *, conservative_auth: bool = False,
) -> bool:
    lowered = value.casefold()
    return (
        "\x00" in value
        or "-----begin private key-----" in lowered
        or _contains_auth_credential(value, conservative_auth)
        or _contains_sensitive_assignment(value)
        or _CREDENTIAL_PREFIX.search(value) is not None
    )


def _contains_auth_credential(value: str, conservative: bool) -> bool:
    match = _AUTH_CREDENTIAL_PATTERN.search(value) if conservative else _AUTH_CREDENTIAL_PATTERN.fullmatch(value.strip())
    if match is None:
        return False
    return conservative or _looks_like_credential_token(match.group("token"))


def _looks_like_credential_token(token: str) -> bool:
    return (
        _CREDENTIAL_PREFIX.search(token) is not None
        or any(character.isdigit() for character in token)
        or any(character in "._~+/=-" for character in token)
        or len(token) >= 24
    )


def _contains_sensitive_assignment(value: str) -> bool:
    return any(
        _is_sensitive_key(match.group("key"))
        for match in _ASSIGNMENT_PATTERN.finditer(value)
    )


def _has_control_character(value: str) -> bool:
    return any(ord(character) < 32 or ord(character) == 127 for character in value)


def _is_bounded_url_text(value: str) -> bool:
    return (
        0 < len(value) <= _MAX_URL_LENGTH
        and not any(character.isspace() for character in value)
        and not _has_control_character(value)
    )


def _has_valid_url_structure(value: str, parsed: Any, port: int | None) -> bool:
    return (
        parsed.scheme.casefold() in {"http", "https"}
        and bool(parsed.netloc)
        and "%" not in parsed.netloc
        and parsed.username is None
        and parsed.password is None
        and "#" not in value
        and _has_valid_port(parsed.netloc, port)
    )


def _has_valid_port(netloc: str, port: int | None) -> bool:
    authority = netloc.rsplit("@", 1)[-1]
    if authority.startswith("["):
        suffix = authority[authority.find("]") + 1:]
        raw_port = suffix[1:] if suffix.startswith(":") else None
    else:
        raw_port = authority.rsplit(":", 1)[1] if ":" in authority else None
    if raw_port is None:
        return True
    return raw_port.isdigit() and port is not None and 1 <= port <= 65535


def _is_valid_host(host: str | None) -> bool:
    if not host:
        return False
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        pass
    numeric_dotted = all(character.isdigit() or character == "." for character in host)
    if numeric_dotted or len(host) > 253 or not host.isascii():
        return False
    return all(_DNS_LABEL.fullmatch(label) for label in host.split("."))


def _query_has_forbidden_data(query: str) -> bool:
    for part in re.split(r"[&;]", query):
        key, _, raw_value = part.partition("=")
        if "%" in key or _is_sensitive_key(key):
            return True
        if _component_has_forbidden_data(raw_value, plus=True):
            return True
    return False


def _component_has_forbidden_data(value: str, *, plus: bool = False) -> bool:
    current = value
    for _ in range(5):
        if _contains_structured_secret(current, conservative_auth=True):
            return True
        if "%" not in current:
            return False
        if re.search(r"%(?![0-9a-fA-F]{2})", current):
            return True
        try:
            current = (unquote_plus if plus else unquote)(current, errors="strict")
        except UnicodeDecodeError:
            return True
    return True
