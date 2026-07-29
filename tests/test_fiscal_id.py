"""PR-COMP-01: Spanish NIF/CIF/NIE check-digit validators."""

import os
import sys

import pytest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core_engine.validators.fiscal_id import (
    FiscalIdError,
    is_valid_fiscal_id,
    normalize_fiscal_id,
    validate_fiscal_id,
)


VALID_IDS = [
    # NIF
    "12345678Z",
    "87654321X",
    "11111111H",
    "00000000T",
    # NIE
    "X1234567L",
    "Y1234567X",
    "Z1234567R",
    # CIF
    "B12345674",
    "A11111119",
    "B99999997",
    "A98765431",
    "Q1234567D",  # letter control org type
]


class TestFiscalId:
    def test_valid_nif_cif_nie_accepted(self):
        for tax_id in VALID_IDS:
            assert is_valid_fiscal_id(tax_id), tax_id
            assert validate_fiscal_id(tax_id) == tax_id.upper()

    def test_invalid_check_digit_rejected(self):
        bad = [
            "12345678A",  # wrong NIF letter
            "B12345678",  # wrong CIF control
            "A11111111",  # wrong CIF control
            "X1234567A",  # wrong NIE letter
            "NOTATAXID",
            "1234567",  # too short
        ]
        for tax_id in bad:
            assert not is_valid_fiscal_id(tax_id), tax_id
            with pytest.raises(FiscalIdError):
                validate_fiscal_id(tax_id)

    def test_normalization_spaces_hyphens_case(self):
        assert normalize_fiscal_id("  b-123 4567-4 ") == "B12345674"
        assert validate_fiscal_id("x-1234567-l") == "X1234567L"
        assert validate_fiscal_id("12345678z") == "12345678Z"
