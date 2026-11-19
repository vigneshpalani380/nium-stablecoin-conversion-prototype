from decimal import Decimal

import pytest

from backend.domain.errors import AppError
from backend.domain.money import format_minor, from_minor, parse_amount, to_minor
from backend.services.quotes.calculator import calculate_quote


def test_prd_example_10000_usd_to_usdc():
    c = calculate_quote(Decimal("10000.00"), Decimal("0.005"), Decimal("1.0000"), 2, 6)
    assert (c.fee, c.net_source, c.destination) == (Decimal("50.00"), Decimal("9950.00"), Decimal("9950.000000"))


def test_fee_and_destination_round_half_up():
    # fee 1.234567 * 0.005 = 0.006172835 -> 0.006173; net 1.228394; * 83.25 = 102.2638005 -> 102.26
    c = calculate_quote(Decimal("1.234567"), Decimal("0.005"), Decimal("83.2500"), 6, 2)
    assert c.fee == Decimal("0.006173")
    assert c.net_source == Decimal("1.228394")
    assert c.destination == Decimal("102.26")


def test_half_up_boundary_on_fee():
    # 0.10 * 0.005 = 0.0005 -> rounds up to 0.00? No: quantize to 0.01 -> 0.00 (0.0005 < 0.005)
    assert calculate_quote(Decimal("0.10"), Decimal("0.005"), Decimal("1"), 2, 6).fee == Decimal("0.00")
    # 1.00 * 0.005 = 0.005 -> exactly half -> 0.01
    assert calculate_quote(Decimal("1.00"), Decimal("0.005"), Decimal("1"), 2, 6).fee == Decimal("0.01")


def test_inr_to_usdc_uses_destination_precision():
    c = calculate_quote(Decimal("100000.00"), Decimal("0.005"), Decimal("0.01201201"), 2, 6)
    assert c.net_source == Decimal("99500.00")
    assert c.destination == Decimal("1195.194995")


@pytest.mark.parametrize("raw", ["0", "0.00", "-5", "abc", "", "1e3", "1,000", " ", "1.", ".5", "1234567890123"])
def test_parse_amount_rejects_invalid(raw):
    with pytest.raises(AppError) as exc:
        parse_amount(raw, 2)
    assert exc.value.code == "INVALID_AMOUNT"


def test_parse_amount_rejects_excess_precision_but_allows_trailing_zeros():
    with pytest.raises(AppError) as exc:
        parse_amount("1.001", 2)
    assert exc.value.code == "PRECISION_EXCEEDED"
    assert parse_amount("1.500", 2) == Decimal("1.50")


def test_parse_amount_rejects_non_string_inputs_like_float():
    with pytest.raises(AppError):
        parse_amount(10.5, 2)  # type: ignore[arg-type]


def test_minor_unit_round_trip_is_exact():
    assert to_minor(Decimal("14950.000000"), 6) == 14_950_000_000
    assert from_minor(1_500_000, 2) == Decimal("15000.00")
    assert format_minor(1, 6) == "0.000001"
    with pytest.raises(ValueError):
        to_minor(Decimal("0.001"), 2)
