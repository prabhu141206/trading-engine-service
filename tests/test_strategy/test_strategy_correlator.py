from datetime import datetime

from candle.candle_models import Candle, CandleBatch
from indicators.indicator_models import (
    IndicatorBatch,
    SymbolIndicatorState,
)

from strategy.strategy_correlator import StrategyCorrelator


def create_candle_batch() -> CandleBatch:
    """
    Create a NIFTY 5-minute candle batch for one specific interval.
    """
    start_time = datetime(2026, 8, 23, 10, 15)
    end_time = datetime(2026, 8, 23, 10, 20)

    candle = Candle(
        symbol="NIFTY",
        timeframe="5m",
        start_time=start_time,
        end_time=end_time,
        open=100.0,
        high=105.0,
        low=99.0,
        close=104.0,
    )

    return CandleBatch(
        timeframe="5m",
        start_time=start_time,
        end_time=end_time,
        candles={
            "NIFTY": candle,
        },
    )


def create_indicator_batch() -> IndicatorBatch:
    """
    Create EMA indicator data for the exact same market interval
    as the candle batch.
    """
    start_time = datetime(2026, 8, 23, 10, 15)
    end_time = datetime(2026, 8, 23, 10, 20)

    indicator = SymbolIndicatorState(
        symbol="NIFTY",
        timeframe="5m",
        ema_10=102.5,
        ready=True,
    )

    return IndicatorBatch(
        timeframe="5m",
        start_time=start_time,
        end_time=end_time,
        indicators={
            "NIFTY": indicator,
        },
    )


def test_candle_alone_does_not_create_context():
    """
    Verify that a candle by itself cannot create a StrategyContext.

    The indicator for the same interval is still missing.
    """
    correlator = StrategyCorrelator()

    contexts = correlator.process_candle_batch(
        create_candle_batch()
    )

    assert contexts == []


def test_indicator_alone_does_not_create_context():
    """
    Verify that an indicator by itself cannot create a StrategyContext.

    The corresponding candle is still missing.
    """
    correlator = StrategyCorrelator()

    contexts = correlator.process_indicator_batch(
        create_indicator_batch()
    )

    assert contexts == []


def test_candle_first_then_indicator_creates_context():
    """
    Verify that a context is created when the candle arrives first
    and the matching indicator arrives afterwards.
    """
    correlator = StrategyCorrelator()

    candle_batch = create_candle_batch()
    indicator_batch = create_indicator_batch()

    first_result = correlator.process_candle_batch(
        candle_batch
    )

    second_result = correlator.process_indicator_batch(
        indicator_batch
    )

    assert first_result == []
    assert len(second_result) == 1

    context = second_result[0]

    assert context.symbol == "NIFTY"
    assert context.timeframe == "5m"
    assert context.start_time == candle_batch.start_time
    assert context.end_time == candle_batch.end_time
    assert context.candle == candle_batch.candles["NIFTY"]
    assert context.indicators["EMA_10"] == 102.5


def test_indicator_first_then_candle_creates_context():
    """
    Verify that a context is also created when the indicator arrives
    before the candle.

    This proves that the correlator does not depend on EventBus
    delivery order.
    """
    correlator = StrategyCorrelator()

    candle_batch = create_candle_batch()
    indicator_batch = create_indicator_batch()

    first_result = correlator.process_indicator_batch(
        indicator_batch
    )

    second_result = correlator.process_candle_batch(
        candle_batch
    )

    assert first_result == []
    assert len(second_result) == 1

    context = second_result[0]

    assert context.symbol == "NIFTY"
    assert context.timeframe == "5m"
    assert context.start_time == indicator_batch.start_time
    assert context.end_time == indicator_batch.end_time
    assert context.candle == candle_batch.candles["NIFTY"]
    assert context.indicators["EMA_10"] == 102.5


def test_different_intervals_are_not_correlated():
    """
    Verify that candle and indicator data from different intervals
    cannot accidentally form one StrategyContext.
    """
    correlator = StrategyCorrelator()

    candle_batch = create_candle_batch()

    indicator_batch = create_indicator_batch()

    # Move the indicator to a different 5-minute interval.
    indicator_batch = IndicatorBatch(
        timeframe="5m",
        start_time=datetime(2026, 8, 23, 10, 20),
        end_time=datetime(2026, 8, 23, 10, 25),
        indicators=indicator_batch.indicators,
    )

    correlator.process_candle_batch(candle_batch)

    contexts = correlator.process_indicator_batch(
        indicator_batch
    )

    assert contexts == []


def test_different_symbols_are_not_correlated():
    """
    Verify that data for different symbols cannot form one context.

    NIFTY candle + RELIANCE indicator must never be combined.
    """
    correlator = StrategyCorrelator()

    candle_batch = create_candle_batch()

    indicator_batch = create_indicator_batch()

    indicator_batch = IndicatorBatch(
        timeframe="5m",
        start_time=indicator_batch.start_time,
        end_time=indicator_batch.end_time,
        indicators={
            "RELIANCE": SymbolIndicatorState(
                symbol="RELIANCE",
                timeframe="5m",
                ema_10=2500.0,
                ready=True,
            ),
        },
    )

    correlator.process_candle_batch(candle_batch)

    contexts = correlator.process_indicator_batch(
        indicator_batch
    )

    assert contexts == []


def test_multiple_symbols_are_correlated_independently():
    """
    Verify that multiple symbols inside the same batches produce
    independent StrategyContexts.
    """
    correlator = StrategyCorrelator()

    start_time = datetime(2026, 8, 23, 10, 15)
    end_time = datetime(2026, 8, 23, 10, 20)

    nifty_candle = Candle(
        symbol="NIFTY",
        timeframe="5m",
        start_time=start_time,
        end_time=end_time,
        open=100.0,
        high=105.0,
        low=99.0,
        close=104.0,
    )

    reliance_candle = Candle(
        symbol="RELIANCE",
        timeframe="5m",
        start_time=start_time,
        end_time=end_time,
        open=2500.0,
        high=2520.0,
        low=2490.0,
        close=2510.0,
    )

    candle_batch = CandleBatch(
        timeframe="5m",
        start_time=start_time,
        end_time=end_time,
        candles={
            "NIFTY": nifty_candle,
            "RELIANCE": reliance_candle,
        },
    )

    indicator_batch = IndicatorBatch(
        timeframe="5m",
        start_time=start_time,
        end_time=end_time,
        indicators={
            "NIFTY": SymbolIndicatorState(
                symbol="NIFTY",
                timeframe="5m",
                ema_10=102.5,
            ),
            "RELIANCE": SymbolIndicatorState(
                symbol="RELIANCE",
                timeframe="5m",
                ema_10=2505.0,
            ),
        },
    )

    correlator.process_candle_batch(candle_batch)

    contexts = correlator.process_indicator_batch(
        indicator_batch
    )

    assert len(contexts) == 2

    contexts_by_symbol = {
        context.symbol: context
        for context in contexts
    }

    assert contexts_by_symbol["NIFTY"].indicators["EMA_10"] == 102.5
    assert (
        contexts_by_symbol["RELIANCE"]
        .indicators["EMA_10"]
        == 2505.0
    )