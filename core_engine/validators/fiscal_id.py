"""
Spanish fiscal identification validators (NIF / NIE / CIF).

Implements official check-digit algorithms used by AEAT identification rules:
- NIF (DNI): 8 digits + control letter (TRWAGMYFPDXBNJZSQVHLCKE)
- NIE: X|Y|Z + 7 digits + control letter (prefix mapped to 0|1|2)
- CIF: org letter + 7 digits + control (digit or letter by org type)

Normalization: uppercase, strip spaces/hyphens.
"""

from __future__ import annotations

import re
from typing import Literal

FiscalIdKind = Literal["NIF", "NIE", "CIF"]

_NIF_LETTERS = "TRWAGMYFPDXBNJZSQVHLCKE"
_CIF_CONTROL_LETTERS = "JABCDEFGHI"  # index = control value 0..9
# Org types whose CIF control is a letter (not digit)
_CIF_LETTER_CONTROL_ORGS = frozenset("PQRSNW")
# Valid first letters for Spanish CIF
_CIF_ORG_LETTERS = frozenset("ABCDEFGHJNPQRSUVW")

_SPACE_HYPHEN = re.compile(r"[\s\-]+")


class FiscalIdError(ValueError):
    """Raised when a Spanish tax ID fails format or check-digit validation."""


def normalize_fiscal_id(value: str) -> str:
    """Uppercase and strip spaces/hyphens. Does not validate check digits."""
    if value is None:
        raise FiscalIdError("tax_id is required")
    cleaned = _SPACE_HYPHEN.sub("", str(value).strip().upper())
    if not cleaned:
        raise FiscalIdError("tax_id is empty after normalization")
    return cleaned


def _nif_letter(number: int) -> str:
    return _NIF_LETTERS[number % 23]


def _cif_control_value(digits7: str) -> int:
    even = sum(int(digits7[i]) for i in range(1, 7, 2))
    odd = 0
    for i in range(0, 7, 2):
        doubled = int(digits7[i]) * 2
        odd += doubled // 10 + doubled % 10
    total = even + odd
    unit = total % 10
    return 0 if unit == 0 else 10 - unit


def _is_valid_nif(body: str) -> bool:
    if not re.fullmatch(r"\d{8}[A-Z]", body):
        return False
    number = int(body[:8])
    return body[8] == _nif_letter(number)


def _is_valid_nie(body: str) -> bool:
    if not re.fullmatch(r"[XYZ]\d{7}[A-Z]", body):
        return False
    prefix_map = {"X": "0", "Y": "1", "Z": "2"}
    number = int(prefix_map[body[0]] + body[1:8])
    return body[8] == _nif_letter(number)


def _is_valid_cif(body: str) -> bool:
    if not re.fullmatch(r"[A-Z]\d{7}[A-Z0-9]", body):
        return False
    org = body[0]
    if org not in _CIF_ORG_LETTERS:
        return False
    digits7 = body[1:8]
    control = body[8]
    value = _cif_control_value(digits7)
    if org in _CIF_LETTER_CONTROL_ORGS:
        return control == _CIF_CONTROL_LETTERS[value]
    # Digit control (some systems also accept equivalent letter)
    return control == str(value) or control == _CIF_CONTROL_LETTERS[value]


def classify_fiscal_id(normalized: str) -> FiscalIdKind | None:
    if re.fullmatch(r"\d{8}[A-Z]", normalized):
        return "NIF"
    if re.fullmatch(r"[XYZ]\d{7}[A-Z]", normalized):
        return "NIE"
    if re.fullmatch(r"[A-Z]\d{7}[A-Z0-9]", normalized):
        return "CIF"
    return None


def is_valid_fiscal_id(value: str) -> bool:
    """Return True if value is a valid Spanish NIF, NIE, or CIF (after normalize)."""
    try:
        validate_fiscal_id(value)
        return True
    except FiscalIdError:
        return False


def validate_fiscal_id(value: str) -> str:
    """
    Normalize and validate a Spanish tax ID.

    Returns the normalized value on success.
    Raises FiscalIdError with a clear message on failure.
    """
    normalized = normalize_fiscal_id(value)
    kind = classify_fiscal_id(normalized)
    if kind is None:
        raise FiscalIdError(
            f"tax_id '{normalized}' has invalid format; expected Spanish NIF, NIE, or CIF"
        )
    ok = {
        "NIF": _is_valid_nif,
        "NIE": _is_valid_nie,
        "CIF": _is_valid_cif,
    }[kind](normalized)
    if not ok:
        raise FiscalIdError(
            f"tax_id '{normalized}' failed {kind} check-digit validation"
        )
    return normalized
