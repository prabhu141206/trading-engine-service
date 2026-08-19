from datetime import datetime

from event_system.event import Event
from event_system.event_bus import EventBus
from event_system.event_type import EventType

from candle.candle_builder import CandleBuilder
from candle.candle_timeframe import CandleTimeframe
from market_data.models import Tick


def publish_tick(
    builder: CandleBuilder,
    symbol: str,
    price: float,
    timestamp: datetime,
) -> None:

    builder._on_tick(
        Event(
            event_type=EventType.TICK_RECEIVED,
            payload=Tick(
                symbol=symbol,
                price=price,
                timestamp=timestamp,
            ),
        )
    )


# =========================================================
# Test 1 — Create first candle
# =========================================================

def test_create_first_candle():

    event_bus = EventBus()
    builder = CandleBuilder(event_bus)

    builder.start()

    publish_tick(
        builder,
        "NIFTY",
        100.0,
        datetime(2026, 8, 17, 10, 15, 10),
    )

    candle = builder._current_candles[
        ("NIFTY", CandleTimeframe.FIVE_MINUTES)
    ]

    assert candle.symbol == "NIFTY"
    assert candle.timeframe == "5m"

    assert candle.start_time == datetime(
        2026, 8, 17, 10, 15
    )

    assert candle.end_time == datetime(
        2026, 8, 17, 10, 20
    )

    assert candle.open == 100.0
    assert candle.high == 100.0
    assert candle.low == 100.0
    assert candle.close == 100.0


# =========================================================
# Test 2 — Update OHLC
# =========================================================

def test_update_candle_ohlc():

    event_bus = EventBus()
    builder = CandleBuilder(event_bus)

    builder.start()

    publish_tick(
        builder,
        "NIFTY",
        100.0,
        datetime(2026, 8, 17, 10, 15, 10),
    )

    publish_tick(
        builder,
        "NIFTY",
        105.0,
        datetime(2026, 8, 17, 10, 16, 10),
    )

    publish_tick(
        builder,
        "NIFTY",
        98.0,
        datetime(2026, 8, 17, 10, 17, 10),
    )

    publish_tick(
        builder,
        "NIFTY",
        102.0,
        datetime(2026, 8, 17, 10, 18, 10),
    )

    candle = builder._current_candles[
        ("NIFTY", CandleTimeframe.FIVE_MINUTES)
    ]

    assert candle.open == 100.0
    assert candle.high == 105.0
    assert candle.low == 98.0
    assert candle.close == 102.0


# =========================================================
# Test 3 — Multiple symbols maintain independent candles
# =========================================================

def test_multiple_symbols_have_independent_candles():

    event_bus = EventBus()
    builder = CandleBuilder(event_bus)

    builder.start()

    publish_tick(
        builder,
        "NIFTY",
        100.0,
        datetime(2026, 8, 17, 10, 15, 10),
    )

    publish_tick(
        builder,
        "BANKNIFTY",
        200.0,
        datetime(2026, 8, 17, 10, 15, 20),
    )

    assert (
        "NIFTY",
        CandleTimeframe.FIVE_MINUTES,
    ) in builder._current_candles

    assert (
        "BANKNIFTY",
        CandleTimeframe.FIVE_MINUTES,
    ) in builder._current_candles

    assert (
        builder._current_candles[
            ("NIFTY", CandleTimeframe.FIVE_MINUTES)
        ].close
        == 100.0
    )

    assert (
        builder._current_candles[
            ("BANKNIFTY", CandleTimeframe.FIVE_MINUTES)
        ].close
        == 200.0
    )


# =========================================================
# Test 4 — New interval creates new candle
# =========================================================

def test_new_interval_creates_new_candle():

    event_bus = EventBus()
    builder = CandleBuilder(event_bus)

    builder.start()

    publish_tick(
        builder,
        "NIFTY",
        100.0,
        datetime(2026, 8, 17, 10, 15, 10),
    )

    publish_tick(
        builder,
        "NIFTY",
        110.0,
        datetime(2026, 8, 17, 10, 20, 1),
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


# =========================================================
# Test 5 — Flush multiple symbols into one batch
# =========================================================

def test_flush_interval_creates_one_candle_batch():

    event_bus = EventBus()
    builder = CandleBuilder(event_bus)

    received_batches = []

    def handler(event):
        received_batches.append(event.payload)

    event_bus.subscribe(
        EventType.CANDLE_BATCH_CLOSED,
        handler,
    )

    builder.start()

    publish_tick(
        builder,
        "NIFTY",
        100.0,
        datetime(2026, 8, 17, 10, 15, 10),
    )

    publish_tick(
        builder,
        "NIFTY",
        105.0,
        datetime(2026, 8, 17, 10, 17, 10),
    )

    publish_tick(
        builder,
        "BANKNIFTY",
        200.0,
        datetime(2026, 8, 17, 10, 15, 20),
    )

    publish_tick(
        builder,
        "BANKNIFTY",
        210.0,
        datetime(2026, 8, 17, 10, 18, 20),
    )

    builder.finalize_interval(
        datetime(2026, 8, 17, 10, 15)
    )

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

    assert batch.candles["NIFTY"].open == 100.0
    assert batch.candles["NIFTY"].high == 105.0

    assert batch.candles["BANKNIFTY"].open == 200.0
    assert batch.candles["BANKNIFTY"].high == 210.0


# =========================================================
# Test 6 — Flushed candles are removed from active state
# =========================================================

def test_flush_removes_completed_candles():

    event_bus = EventBus()
    builder = CandleBuilder(event_bus)

    builder.start()

    publish_tick(
        builder,
        "NIFTY",
        100.0,
        datetime(2026, 8, 17, 10, 15, 10),
    )

    publish_tick(
        builder,
        "BANKNIFTY",
        200.0,
        datetime(2026, 8, 17, 10, 15, 20),
    )

    builder.finalize_interval(
        datetime(2026, 8, 17, 10, 15)
    )

    assert (
        "NIFTY",
        CandleTimeframe.FIVE_MINUTES,
    ) not in builder._current_candles

    assert (
        "BANKNIFTY",
        CandleTimeframe.FIVE_MINUTES,
    ) not in builder._current_candles


# =========================================================
# Test 7 — Tick after boundary belongs to new interval
# =========================================================

def test_tick_after_boundary_belongs_to_new_interval():

    event_bus = EventBus()
    builder = CandleBuilder(event_bus)

    builder.start()

    publish_tick(
        builder,
        "NIFTY",
        100.0,
        datetime(2026, 8, 17, 10, 15, 50),
    )

    builder.finalize_interval(
        datetime(2026, 8, 17, 10, 15)
    )

    publish_tick(
        builder,
        "NIFTY",
        110.0,
        datetime(2026, 8, 17, 10, 20, 1),
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


# =========================================================
# Test 8 — Empty interval produces no event
# =========================================================

def test_flush_empty_interval_does_not_publish():

    event_bus = EventBus()
    builder = CandleBuilder(event_bus)

    received_batches = []

    def handler(event):
        received_batches.append(event.payload)

    event_bus.subscribe(
        EventType.CANDLE_BATCH_CLOSED,
        handler,
    )

    builder.start()

    builder.finalize_interval(
        datetime(2026, 8, 17, 10, 15)
    )

    assert len(received_batches) == 0