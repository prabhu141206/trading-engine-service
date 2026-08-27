from datetime import datetime
from unittest.mock import Mock

from candle.candle_models import Candle, CandleBatch
from event_system.event import Event
from event_system.event_type import EventType
from indicators.indicator_models import (
    IndicatorBatch,
    SymbolIndicatorState,
)

from strategy.strategy_correlator import StrategyCorrelator
from strategy.strategy_dispatcher import StrategyDispatcher
from strategy.strategy_engine import StrategyEngine
from strategy.strategy_state import StrategyState
from strategy.strategies.ema_strategy import EMAStrategy


def create_engine():
    """
    Create the real strategy pipeline.

    Only EventBus is mocked because this test verifies the complete
    strategy computation flow rather than the external event system.
    """
    event_bus = Mock()

    strategy = EMAStrategy(
        symbol="NIFTY",
        timeframe="5m",
        parameters=(("period", 10),),
    )

    correlator = StrategyCorrelator()

    dispatcher = StrategyDispatcher(
        strategies=[strategy],
    )

    engine = StrategyEngine(
        event_bus=event_bus,
        correlator=correlator,
        dispatcher=dispatcher,
    )

    return engine, event_bus, strategy


def create_candle(
    open_price: float,
    high: float,
    low: float,
    close: float,
    start_time: datetime,
    end_time: datetime,
) -> Candle:
    """
    Create a NIFTY 5-minute candle for the integration test.
    """
    return Candle(
        symbol="NIFTY",
        timeframe="5m",
        start_time=start_time,
        end_time=end_time,
        open=open_price,
        high=high,
        low=low,
        close=close,
    )


def create_candle_batch(
    candle: Candle,
) -> CandleBatch:
    """
    Wrap one candle into a CandleBatch.
    """
    return CandleBatch(
        timeframe="5m",
        start_time=candle.start_time,
        end_time=candle.end_time,
        candles={
            "NIFTY": candle,
        },
    )


def create_indicator_batch(
    candle: Candle,
    ema: float,
) -> IndicatorBatch:
    """
    Create the EMA indicator batch corresponding to the exact
    candle interval.
    """
    return IndicatorBatch(
        timeframe="5m",
        start_time=candle.start_time,
        end_time=candle.end_time,
        indicators={
            "NIFTY": SymbolIndicatorState(
                symbol="NIFTY",
                timeframe="5m",
                ema_10=ema,
                ready=True,
            ),
        },
    )


def test_complete_long_trade_cycle():
    """
    Verify one complete EMA long trade cycle.

    Flow:

        IDLE
          ↓
        red candle away from EMA
          ↓
        TRIGGER_ARMED
          ↓
        tick breaks trigger high
          ↓
        BUY ENTRY
          ↓
        IN_TRADE
          ↓
        candle closes below EMA
          ↓
        SELL EXIT
          ↓
        IDLE
    """

    engine, event_bus, strategy = create_engine()

    # ---------------------------------------------------------
    # STEP 1
    # Create the trigger candle.
    #
    # Red candle:
    # open  = 105
    # close = 104
    #
    # EMA = 100
    #
    # The entire candle is above EMA.
    # ---------------------------------------------------------

    trigger_candle = create_candle(
        open_price=105.0,
        high=108.0,
        low=103.0,
        close=104.0,
        start_time=datetime(2026, 8, 24, 10, 15),
        end_time=datetime(2026, 8, 24, 10, 20),
    )

    candle_event = Event(
        event_type=EventType.CANDLE_BATCH_CLOSED,
        payload=create_candle_batch(
            trigger_candle
        ),
    )

    indicator_event = Event(
        event_type=EventType.INDICATOR_BATCH_UPDATED,
        payload=create_indicator_batch(
            trigger_candle,
            ema=100.0,
        ),
    )

    # Send candle first.
    engine._on_candle_batch(
        candle_event
    )

    # No complete context exists yet.
    assert strategy.state is StrategyState.IDLE

    # Send matching indicator.
    engine._on_indicator_batch(
        indicator_event
    )

    # Strategy should now be armed.
    assert strategy.state is StrategyState.TRIGGER_ARMED

    # No signal should have been published yet.
    event_bus.publish.assert_not_called()

    # ---------------------------------------------------------
    # STEP 2
    # Tick breaks trigger candle high.
    # ---------------------------------------------------------

    tick_context = Mock()

    tick_context.symbol = "NIFTY"
    tick_context.timeframe = "5m"
    tick_context.start_time = trigger_candle.start_time
    tick_context.end_time = trigger_candle.end_time
    tick_context.candle = trigger_candle
    tick_context.indicators = {
        "EMA_10": 100.0,
    }

    # The current implementation accepts a numeric tick.
    tick_context.tick = 108.1

    tick_event = Event(
        event_type=EventType.TICK_RECEIVED,
        payload=tick_context,
    )

    engine._on_tick(
        tick_event
    )

    # Strategy should now be in trade.
    assert strategy.state is StrategyState.IN_TRADE

    # Exactly one event should have been generated.
    assert event_bus.publish.call_count == 1

    entry_event = (
        event_bus.publish.call_args_list[0]
        .args[0]
    )

    assert (
        entry_event.event_type
        is EventType.STRATEGY_SIGNAL_GENERATED
    )

    # Verify the exact strategy computation.
    assert (
        entry_event.payload.strategy_group.strategy_type
        == "EMA"
    )

    assert (
        entry_event.payload.strategy_group.symbol
        == "NIFTY"
    )

    assert (
        entry_event.payload.strategy_group.timeframe
        == "5m"
    )

    assert (
        entry_event.payload.strategy_group.parameters
        == (("period", 10),)
    )

    # Verify the entry signal.
    assert (
        entry_event.payload.signal_type
        == "ENTRY"
    )

    assert (
        entry_event.payload.side
        == "BUY"
    )

    # ---------------------------------------------------------
    # STEP 3
    # Create a candle that closes below EMA 10.
    # ---------------------------------------------------------

    exit_candle = create_candle(
        open_price=102.0,
        high=103.0,
        low=98.0,
        close=99.0,
        start_time=datetime(2026, 8, 24, 10, 20),
        end_time=datetime(2026, 8, 24, 10, 25),
    )

    exit_candle_event = Event(
        event_type=EventType.CANDLE_BATCH_CLOSED,
        payload=create_candle_batch(
            exit_candle
        ),
    )

    exit_indicator_event = Event(
        event_type=EventType.INDICATOR_BATCH_UPDATED,
        payload=create_indicator_batch(
            exit_candle,
            ema=100.0,
        ),
    )

    # Candle arrives first.
    engine._on_candle_batch(
        exit_candle_event
    )

    # Then matching indicator arrives.
    engine._on_indicator_batch(
        exit_indicator_event
    )

    # ---------------------------------------------------------
    # STEP 4
    # Verify exit.
    # ---------------------------------------------------------

    assert strategy.state is StrategyState.IDLE

    # Entry + Exit = 2 published events.
    assert event_bus.publish.call_count == 2

    exit_event = (
        event_bus.publish.call_args_list[1]
        .args[0]
    )

    assert (
        exit_event.event_type
        is EventType.STRATEGY_SIGNAL_GENERATED
    )

    # Verify the exact strategy computation.
    assert (
        exit_event.payload.strategy_group.strategy_type
        == "EMA"
    )

    assert (
        exit_event.payload.strategy_group.symbol
        == "NIFTY"
    )

    assert (
        exit_event.payload.strategy_group.timeframe
        == "5m"
    )

    assert (
        exit_event.payload.strategy_group.parameters
        == (("period", 10),)
    )

    # Verify the exit signal.
    assert (
        exit_event.payload.signal_type
        == "EXIT"
    )

    assert (
        exit_event.payload.side
        == "SELL"
    )