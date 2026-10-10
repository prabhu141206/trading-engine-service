
from datetime import datetime, timedelta

from event_system.event import Event
from event_system.event_bus import EventBus
from event_system.event_type import EventType

from candle.candle_builder import CandleBuilder
from candle.candle_scheduler import CandleScheduler
from candle.candle_session_manager import CandleSessionManager
from candle.candle_timeframe import CandleTimeframe
from market_data.models import Tick


def test_full_market_shutdown_finalizes_candle_before_completion():
    # Arrange: use the real event bus, builder, scheduler and manager.
    event_bus = EventBus()
    candle_builder = CandleBuilder(event_bus=event_bus)

    candle_scheduler = CandleScheduler(
        timeframe=CandleTimeframe.FIVE_MINUTES,
        on_boundary=candle_builder.finalize_interval,
    )

    candle_session_manager = CandleSessionManager(
        event_bus=event_bus,
        candle_scheduler=candle_scheduler,
    )

    candle_builder.start()
    candle_session_manager.start()

    events = []

    event_bus.subscribe(
        EventType.CANDLE_BATCH_CLOSED,
        lambda event: events.append(event),
    )
    event_bus.subscribe(
        EventType.MARKET_PROCESSING_COMPLETE,
        lambda event: events.append(event),
    )

    # Use a fixed timestamp so the expected candle interval is deterministic.
    tick_time = datetime(2026, 9, 27, 14, 56, 0)
    final_boundary = datetime(2026, 9, 27, 15, 0, 0)
    interval_start = final_boundary - timedelta(minutes=5)

    tick = Tick(
        symbol="NIFTY",
        price=25100.0,
        timestamp=tick_time,
    )

    # Act: build the candle, then close the market.
    event_bus.publish(
        Event(
            event_type=EventType.TICK_RECEIVED,
            payload=tick,
        )
    )

    # Start the real scheduler so stop_after_boundary() executes
    # its final-boundary callback. The close event stops it immediately.
    candle_scheduler.start()

    event_bus.publish(
        Event(
            event_type=EventType.MARKET_CLOSE,
            payload=final_boundary,
        )
    )

    # Assert: the final candle is published before processing completes.
    assert [event.event_type for event in events] == [
        EventType.CANDLE_BATCH_CLOSED,
        EventType.MARKET_PROCESSING_COMPLETE,
    ]

    batch = events[0].payload
    candle = batch.candles["NIFTY"]

    assert batch.start_time == interval_start
    assert batch.end_time == final_boundary

    assert candle.open == 25100.0
    assert candle.high == 25100.0
    assert candle.low == 25100.0
    assert candle.close == 25100.0

    # The completed candle must no longer be in active builder state.
    assert (
        "NIFTY",
        CandleTimeframe.FIVE_MINUTES,
    ) not in candle_builder._current_candles




def test_market_close_does_not_silently_skip_final_candle_when_scheduler_is_stopped():
    event_bus = EventBus()
    candle_builder = CandleBuilder(event_bus=event_bus)

    candle_scheduler = CandleScheduler(
        timeframe=CandleTimeframe.FIVE_MINUTES,
        on_boundary=candle_builder.finalize_interval,
    )

    candle_session_manager = CandleSessionManager(
        event_bus=event_bus,
        candle_scheduler=candle_scheduler,
    )

    candle_builder.start()
    candle_session_manager.start()

    events = []

    event_bus.subscribe(
        EventType.CANDLE_BATCH_CLOSED,
        lambda event: events.append(event),
    )
    event_bus.subscribe(
        EventType.MARKET_PROCESSING_COMPLETE,
        lambda event: events.append(event),
    )

    tick = Tick(
        symbol="NIFTY",
        price=25100.0,
        timestamp=datetime(2026, 9, 27, 14, 56, 0),
    )

    event_bus.publish(
        Event(
            event_type=EventType.TICK_RECEIVED,
            payload=tick,
        )
    )

    final_boundary = datetime(2026, 9, 27, 15, 0, 0)

    event_bus.publish(
        Event(
            event_type=EventType.MARKET_CLOSE,
            payload=final_boundary,
        )
    )

    # The final candle should be processed before shutdown completes.
    assert [event.event_type for event in events] == [
        EventType.CANDLE_BATCH_CLOSED,
        EventType.MARKET_PROCESSING_COMPLETE,
    ]


def test_repeated_market_close_publishes_completion_only_once():
    event_bus = EventBus()
    candle_builder = CandleBuilder(event_bus=event_bus)

    candle_scheduler = CandleScheduler(
        timeframe=CandleTimeframe.FIVE_MINUTES,
        on_boundary=candle_builder.finalize_interval,
    )

    candle_session_manager = CandleSessionManager(
        event_bus=event_bus,
        candle_scheduler=candle_scheduler,
    )

    candle_builder.start()
    candle_session_manager.start()

    candle_batches = []
    completion_events = []

    event_bus.subscribe(
        EventType.CANDLE_BATCH_CLOSED,
        lambda event: candle_batches.append(event),
    )
    event_bus.subscribe(
        EventType.MARKET_PROCESSING_COMPLETE,
        lambda event: completion_events.append(event),
    )

    event_bus.publish(
        Event(
            event_type=EventType.TICK_RECEIVED,
            payload=Tick(
                symbol="NIFTY",
                price=25100.0,
                timestamp=datetime(2026, 9, 27, 14, 56, 0),
            ),
        )
    )

    market_close = Event(
        event_type=EventType.MARKET_CLOSE,
        payload=datetime(2026, 9, 27, 15, 0, 0),
    )

    event_bus.publish(market_close)
    event_bus.publish(market_close)

    assert len(candle_batches) == 1
    assert len(completion_events) == 1
