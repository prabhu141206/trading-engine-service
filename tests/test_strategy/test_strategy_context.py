from datetime import datetime

from candle.candle_models import Candle
from strategy.strategy_context import StrategyContext


def test_strategy_context():
    """
    Verify that a strategy context can represent one complete
    market-data interval.

    The context contains:
        - symbol
        - timeframe
        - interval start and end
        - candle
        - indicator values

    Tick data remains optional.
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

    context = StrategyContext(
        symbol="NIFTY",
        timeframe="5m",
        start_time=start_time,
        end_time=end_time,
        candle=candle,
        indicators={"EMA_10": 102.5},
    )

    assert context.symbol == "NIFTY"
    assert context.timeframe == "5m"
    assert context.start_time == start_time
    assert context.end_time == end_time
    assert context.candle == candle
    assert context.indicators["EMA_10"] == 102.5
    assert context.tick is None