from __future__ import annotations

import re
from typing import Any


USERNAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{2,63}$")
EMPLOYEE_CODE_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9-]{1,31}$")
FORBIDDEN_TEXT_CHARS = frozenset("<>{}")


def collapse_spaces(value: str) -> str:
    return " ".join(value.strip().split())


def normalize_username(value: Any) -> str:
    if not isinstance(value, str):
        raise ValueError("Username must be a string.")

    normalized = value.strip().lower()
    if not USERNAME_PATTERN.fullmatch(normalized):
        raise ValueError(
            "Username must be 3-64 characters and contain only letters, numbers, dot, dash, or underscore."
        )
    return normalized


def normalize_employee_code(value: Any) -> str:
    if not isinstance(value, str):
        raise ValueError("Employee code must be a string.")

    normalized = value.strip().upper()
    if not EMPLOYEE_CODE_PATTERN.fullmatch(normalized):
        raise ValueError(
            "Employee code must be 2-32 uppercase letters, numbers, or dashes, for example E001 or EMP0001."
        )
    return normalized


def normalize_business_text(
    value: Any,
    *,
    field_label: str,
    min_length: int,
    max_length: int,
) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field_label} must be a string.")

    normalized = collapse_spaces(value)
    if len(normalized) < min_length:
        raise ValueError(f"{field_label} must be at least {min_length} characters.")
    if len(normalized) > max_length:
        raise ValueError(f"{field_label} must be at most {max_length} characters.")
    if any(char in FORBIDDEN_TEXT_CHARS or ord(char) < 32 for char in normalized):
        raise ValueError(f"{field_label} contains unsupported characters.")
    return normalized


def validate_password_strength(value: str) -> str:
    if value != value.strip():
        raise ValueError("Password must not start or end with spaces.")
    if len(value) < 8:
        raise ValueError("Password must be at least 8 characters.")
    if len(value) > 128:
        raise ValueError("Password must be at most 128 characters.")
    if not any(char.isalpha() for char in value) or not any(char.isdigit() for char in value):
        raise ValueError("Password must include at least one letter and one number.")
    return value
