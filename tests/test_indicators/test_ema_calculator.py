import pytest

from indicators.ema_calculator import EMACalculator


# =========================================================
# Test 1 — Reject invalid EMA period
# =========================================================

def test_ema_calculator_rejects_invalid_period():
    """
    Verify that EMACalculator rejects an invalid EMA period.

    A period of 0 is not valid, so the calculator should
    raise a ValueError during initialization.
    """

    with pytest.raises(ValueError):
        EMACalculator(0)


# =========================================================
# Test 2 — Reject empty close-price input
# =========================================================

def test_ema_calculator_rejects_empty_closes():
    """
    Verify that EMA calculation rejects an empty list of
    closing prices.

    At least one closing price is required to calculate an EMA.
    """

    calculator = EMACalculator(10)

    with pytest.raises(ValueError):
        calculator.calculate_from_closes([])


# =========================================================
# Test 3 — Single close price
# =========================================================

def test_single_close_returns_that_close():
    """
    Verify that when only one closing price is available,
    that price itself is returned as the EMA value.

    This establishes the initial EMA value.
    """

    calculator = EMACalculator(10)

    result = calculator.calculate_from_closes(
        [100.0]
    )

    assert result == 100.0


# =========================================================
# Test 4 — Full EMA calculation
# =========================================================

def test_ema_calculation():
    """
    Verify that EMACalculator correctly calculates EMA
    from a sequence of closing prices.

    The expected EMA is calculated independently using
    the EMA formula and then compared with the calculator's
    result.
    """

    calculator = EMACalculator(10)

    closes = [
        100.0,
        105.0,
        102.0,
        108.0,
    ]

    result = calculator.calculate_from_closes(
        closes
    )

    # EMA smoothing factor:
    # alpha = 2 / (period + 1)
    alpha = 2 / 11

    # The first close is used as the initial EMA.
    expected = 100.0

    # Calculate the expected EMA independently.
    for close in closes[1:]:
        expected = (
            close * alpha
            + expected * (1 - alpha)
        )

    # Compare using pytest.approx() because EMA involves
    # floating-point arithmetic.
    assert result == pytest.approx(
        expected
    )


# =========================================================
# Test 5 — Incremental update consistency
# =========================================================

def test_incremental_update_matches_full_calculation():
    """
    Verify that updating an existing EMA with a new close
    produces the same result as recalculating the EMA from
    the complete close-price history.
    """

    calculator = EMACalculator(10)

    historical_closes = [
        100.0,
        105.0,
        102.0,
        108.0,
    ]

    # First calculate the EMA from the existing history.
    historical_ema = (
        calculator.calculate_from_closes(
            historical_closes
        )
    )

    # Update the existing EMA using the new closing price.
    updated_ema = calculator.update(
        previous_ema=historical_ema,
        close=110.0,
    )

    # Independently calculate the EMA again using the
    # complete history including the new closing price.
    expected = (
        calculator.calculate_from_closes(
            historical_closes + [110.0]
        )
    )

    # Both approaches should produce the same EMA value.
    assert updated_ema == pytest.approx(
        expected
    )