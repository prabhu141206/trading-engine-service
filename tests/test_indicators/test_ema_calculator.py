
import pytest

from indicators.ema_calculator import EMACalculator


def test_ema_calculator_rejects_invalid_period():

    with pytest.raises(ValueError):

        EMACalculator(0)


def test_ema_calculator_rejects_empty_closes():

    calculator = EMACalculator(10)

    with pytest.raises(ValueError):

        calculator.calculate_from_closes([])


def test_single_close_returns_that_close():

    calculator = EMACalculator(10)

    result = calculator.calculate_from_closes(
        [100.0]
    )

    assert result == 100.0


def test_ema_calculation():

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

    alpha = 2 / 11

    expected = 100.0

    for close in closes[1:]:
        expected = (
            close * alpha
            + expected * (1 - alpha)
        )

    assert result == pytest.approx(
        expected
    )


def test_incremental_update_matches_full_calculation():

    calculator = EMACalculator(10)

    historical_closes = [
        100.0,
        105.0,
        102.0,
        108.0,
    ]

    historical_ema = (
        calculator.calculate_from_closes(
            historical_closes
        )
    )

    updated_ema = calculator.update(
        previous_ema=historical_ema,
        close=110.0,
    )

    expected = (
        calculator.calculate_from_closes(
            historical_closes + [110.0]
        )
    )

    assert updated_ema == pytest.approx(
        expected
    )