from datetime import datetime

from event_system.event_bus import EventBus
from event_system.event_type import EventType

from candle.candle_builder import CandleBuilder
from candle.candle_scheduler import CandleScheduler
from candle.candle_timeframe import CandleTimeframe
from market_data.models import Tick


def test_scheduler_flushes_candle_batch():
    event_bus = EventBus()

    builder = CandleBuilder(event_bus)

    scheduler = CandleScheduler(
        timeframe=CandleTimeframe.FIVE_MINUTES,
        on_boundary=builder.finalize_interval,
    )

    received_batches = []

    def handler(event):
        received_batches.append(event.payload)

    event_bus.subscribe(
        EventType.CANDLE_BATCH_CLOSED,
        handler,
    )

    builder.start()

    # ---------------------------------------------------------
    # NIFTY ticks during 10:15 - 10:20
    # ---------------------------------------------------------

    builder._process_tick(
        Tick(
            symbol="NIFTY",
            price=100.0,
            timestamp=datetime(
                2026, 8, 17, 10, 15, 10
            ),
        )
    )

    builder._process_tick(
        Tick(
            symbol="NIFTY",
            price=105.0,
            timestamp=datetime(
                2026, 8, 17, 10, 17, 10
            ),
        )
    )

    # ---------------------------------------------------------
    # BANKNIFTY ticks during same interval
    # ---------------------------------------------------------

    builder._process_tick(
        Tick(
            symbol="BANKNIFTY",
            price=200.0,
            timestamp=datetime(
                2026, 8, 17, 10, 15, 20
            ),
        )
    )

    builder._process_tick(
        Tick(
            symbol="BANKNIFTY",
            price=210.0,
            timestamp=datetime(
                2026, 8, 17, 10, 18, 20
            ),
        )
    )

    # ---------------------------------------------------------
    # Scheduler determines next boundary
    # ---------------------------------------------------------

    boundary = scheduler.get_next_boundary(
        datetime(
            2026, 8, 17, 10, 19, 30
        )
    )

    assert boundary == datetime(
        2026, 8, 17, 10, 20
    )

    interval_start = (
        scheduler.get_interval_start(boundary)
    )

    assert interval_start == datetime(
        2026, 8, 17, 10, 15
    )

    # ---------------------------------------------------------
    # Flush completed interval
    # ---------------------------------------------------------

    scheduler.trigger_boundary(boundary)

    # ---------------------------------------------------------
    # Verify one batch
    # ---------------------------------------------------------

    assert len(received_batches) == 1

    batch = received_batches[0]

    assert batch.timeframe == "5m"

    assert batch.start_time == datetime(
        2026, 8, 17, 10, 15
    )

    assert batch.end_time == datetime(
        2026, 8, 17, 10, 20
    )

    assert set(batch.candles.keys()) == {
        "NIFTY",
        "BANKNIFTY",
    }

    # NIFTY
    assert batch.candles["NIFTY"].open == 100.0
    assert batch.candles["NIFTY"].high == 105.0
    assert batch.candles["NIFTY"].low == 100.0
    assert batch.candles["NIFTY"].close == 105.0

    # BANKNIFTY
    assert batch.candles["BANKNIFTY"].open == 200.0
    assert batch.candles["BANKNIFTY"].high == 210.0
    assert batch.candles["BANKNIFTY"].low == 200.0
    assert batch.candles["BANKNIFTY"].close == 210.0


def test_tick_after_flush_starts_next_candle():
    event_bus = EventBus()

    builder = CandleBuilder(event_bus)

    builder.start()

    # 10:15 - 10:20 candle
    builder._process_tick(
        Tick(
            symbol="NIFTY",
            price=100.0,
            timestamp=datetime(
                2026, 8, 17, 10, 15, 10
            ),
        )
    )

    builder.finalize_interval(
        datetime(
            2026, 8, 17, 10, 15
        )
    )

    # Tick arrives after 10:20
    builder._process_tick(
        Tick(
            symbol="NIFTY",
            price=110.0,
            timestamp=datetime(
                2026, 8, 17, 10, 20, 1
            ),
        )
    )

    candle = builder._current_candles[
        ("NIFTY", CandleTimeframe.FIVE_MINUTES)
    ]

    assert candle.start_time == datetime(
        2026, 8, 17, 10, 20
    )

    assert candle.end_time == datetime(
        2026, 8, 17, 10, 25
    )

    assert candle.open == 110.0
    assert candle.high == 110.0
    assert candle.low == 110.0
    assert candle.close == 110.0




def test_start_creates_scheduler_thread():

    scheduler = CandleScheduler(
        timeframe=CandleTimeframe.FIVE_MINUTES,
        on_boundary=lambda interval_start: None,
    )

    scheduler.start()

    assert scheduler._running is True
    assert scheduler._thread is not None
    assert scheduler._thread.is_alive()

    scheduler.stop()

def test_stop_stops_scheduler_thread():

    scheduler = CandleScheduler(
        timeframe=CandleTimeframe.FIVE_MINUTES,
        on_boundary=lambda interval_start: None,
    )

    scheduler.start()
    scheduler.stop()

    assert scheduler._running is False
    assert scheduler._thread is None