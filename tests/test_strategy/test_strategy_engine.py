from datetime import datetime
from unittest.mock import Mock

from candle.candle_models import CandleBatch
from indicators.indicator_models import IndicatorBatch

from strategy.strategy_engine import StrategyEngine
from strategy.strategy_context import StrategyContext


def create_candle_batch() -> CandleBatch:
    """
    Create a minimal candle batch for StrategyEngine tests.
    """
    return CandleBatch(
        timeframe="5m",
        start_time=datetime(2026, 8, 23, 10, 15),
        end_time=datetime(2026, 8, 23, 10, 20),
        candles={},
    )


def create_indicator_batch() -> IndicatorBatch:
    """
    Create a minimal indicator batch for StrategyEngine tests.
    """
    return IndicatorBatch(
        timeframe="5m",
        start_time=datetime(2026, 8, 23, 10, 15),
        end_time=datetime(2026, 8, 23, 10, 20),
        indicators={},
    )


def create_context() -> StrategyContext:
    """
    Create a minimal completed StrategyContext.
    """
    return StrategyContext(
        symbol="NIFTY",
        timeframe="5m",
        start_time=datetime(2026, 8, 23, 10, 15),
        end_time=datetime(2026, 8, 23, 10, 20),
    )


def create_engine():
    """
    Create a StrategyEngine with mocked dependencies.

    Dispatcher methods return empty output lists because the engine
    expects the dispatcher to return StrategyOutput objects.
    """
    event_bus = Mock()
    correlator = Mock()
    dispatcher = Mock()

    dispatcher.dispatch_context.return_value = []
    dispatcher.dispatch_tick.return_value = []

    engine = StrategyEngine(
        event_bus=event_bus,
        correlator=correlator,
        dispatcher=dispatcher,
    )

    return engine, event_bus, correlator, dispatcher

def test_start_subscribes_to_required_events():
    """
    Verify that StrategyEngine subscribes to all market-data events
    required for strategy processing.

    The engine must receive:
        - completed candle batches
        - updated indicator batches
        - ticks
    """
    engine, event_bus, _, _ = create_engine()

    engine.start()

    assert event_bus.subscribe.call_count == 3

    subscribed_events = {
        call.args[0]
        for call in event_bus.subscribe.call_args_list
    }

    from event_system.event_type import EventType

    assert EventType.CANDLE_BATCH_CLOSED in subscribed_events
    assert EventType.INDICATOR_BATCH_UPDATED in subscribed_events
    assert EventType.TICK_RECEIVED in subscribed_events


def test_candle_event_is_sent_to_correlator():
    """
    Verify that a CandleBatch event enters the correlation layer.

    StrategyEngine should orchestrate the flow rather than perform
    candle/indicator matching itself.
    """
    engine, _, correlator, _ = create_engine()

    batch = create_candle_batch()

    correlator.process_candle_batch.return_value = []

    from event_system.event import Event
    from event_system.event_type import EventType

    event = Event(
        event_type=EventType.CANDLE_BATCH_CLOSED,
        payload=batch,
    )

    engine._on_candle_batch(event)

    correlator.process_candle_batch.assert_called_once_with(batch)


def test_indicator_event_is_sent_to_correlator():
    """
    Verify that an IndicatorBatch event enters the correlation layer.

    The engine does not decide whether the indicator matches a candle.
    That responsibility belongs to StrategyCorrelator.
    """
    engine, _, correlator, _ = create_engine()

    batch = create_indicator_batch()

    correlator.process_indicator_batch.return_value = []

    from event_system.event import Event
    from event_system.event_type import EventType

    event = Event(
        event_type=EventType.INDICATOR_BATCH_UPDATED,
        payload=batch,
    )

    engine._on_indicator_batch(event)

    correlator.process_indicator_batch.assert_called_once_with(batch)


def test_completed_context_is_sent_to_dispatcher():
    """
    Verify that contexts produced by the correlator are forwarded
    to the StrategyDispatcher.

    The engine should not perform strategy-specific routing itself.
    """
    engine, _, correlator, dispatcher = create_engine()

    context = create_context()

    correlator.process_candle_batch.return_value = [
        context
    ]

    batch = create_candle_batch()

    from event_system.event import Event
    from event_system.event_type import EventType

    event = Event(
        event_type=EventType.CANDLE_BATCH_CLOSED,
        payload=batch,
    )

    engine._on_candle_batch(event)

    dispatcher.dispatch_context.assert_called_once_with(
        context
    )


def test_multiple_completed_contexts_are_all_dispatched():
    """
    Verify that every completed context returned by the correlator
    is forwarded to the dispatcher.

    This is required because one CandleBatch can contain multiple
    symbols.
    """
    engine, _, correlator, dispatcher = create_engine()

    context_one = create_context()

    context_two = StrategyContext(
        symbol="RELIANCE",
        timeframe="5m",
        start_time=datetime(2026, 8, 23, 10, 15),
        end_time=datetime(2026, 8, 23, 10, 20),
    )

    correlator.process_candle_batch.return_value = [
        context_one,
        context_two,
    ]

    batch = create_candle_batch()

    from event_system.event import Event
    from event_system.event_type import EventType

    event = Event(
        event_type=EventType.CANDLE_BATCH_CLOSED,
        payload=batch,
    )

    engine._on_candle_batch(event)

    assert dispatcher.dispatch_context.call_count == 2

    dispatcher.dispatch_context.assert_any_call(
        context_one
    )

    dispatcher.dispatch_context.assert_any_call(
        context_two
    )


def test_tick_event_is_sent_directly_to_dispatcher():
    """
    Verify that tick data bypasses the candle/indicator correlator.

    Tick routing is handled directly by StrategyDispatcher, which
    decides which strategies require tick data.
    """
    engine, _, correlator, dispatcher = create_engine()

    tick_context = create_context()

    from event_system.event import Event
    from event_system.event_type import EventType

    event = Event(
        event_type=EventType.TICK_RECEIVED,
        payload=tick_context,
    )

    engine._on_tick(event)

    dispatcher.dispatch_tick.assert_called_once_with(
        tick_context
    )

    correlator.process_candle_batch.assert_not_called()
    correlator.process_indicator_batch.assert_not_called()


def test_no_completed_context_means_nothing_is_dispatched():
    """
    Verify that the engine does not call the dispatcher when the
    correlator has not yet received enough data to build a context.

    This represents the normal situation where one event arrives
    before its matching event.
    """
    engine, _, correlator, dispatcher = create_engine()

    correlator.process_candle_batch.return_value = []

    batch = create_candle_batch()

    from event_system.event import Event
    from event_system.event_type import EventType

    event = Event(
        event_type=EventType.CANDLE_BATCH_CLOSED,
        payload=batch,
    )

    engine._on_candle_batch(event)

    dispatcher.dispatch_context.assert_not_called()