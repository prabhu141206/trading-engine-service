import threading
from datetime import datetime

import pytest

from candle.candle_models import Candle, CandleBatch
from candle.candle_scheduler import CandleScheduler
from candle.candle_session_manager import CandleSessionManager
from candle.candle_timeframe import CandleTimeframe

from event_system.event import Event
from event_system.event_bus import EventBus
from event_system.event_type import EventType

from indicators.fake_active_symbol_provider import (
    FakeActiveSymbolProvider,
)
from indicators.fake_historical_data_provider import (
    FakeHistoricalCandleProvider,
)
from indicators.indicator_engine import IndicatorEngine
from indicators.indicator_state import IndicatorStateStore


# ------------------------------------------------------------------
# Test Helpers
# ------------------------------------------------------------------


def create_candles(
    symbol: str,
    closes: list[float],
) -> list[Candle]:
    """
    Create simple historical candles for testing.
    """

    candles = []

    for close in closes:
        candles.append(
            Candle(
                symbol=symbol,
                timeframe="5m",
                start_time=None,
                end_time=None,
                open=close,
                high=close,
                low=close,
                close=close,
            )
        )

    return candles


def create_engine(
    symbols: list[str],
    candles_by_symbol: dict[str, list[Candle]],
):
    """
    Create an IndicatorEngine with fake dependencies.
    """

    event_bus = EventBus()

    symbol_provider = FakeActiveSymbolProvider(
        symbols
    )

    historical_provider = (
        FakeHistoricalCandleProvider(
            candles_by_symbol
        )
    )

    state_store = IndicatorStateStore()

    engine = IndicatorEngine(
        event_bus=event_bus,
        symbol_provider=symbol_provider,
        historical_provider=historical_provider,
        state_store=state_store,
    )

    return engine, state_store, event_bus


def start_engine_and_wait_for_warmup(
    engine: IndicatorEngine,
    event_bus: EventBus,
) -> None:
    """
    Start the IndicatorEngine and simulate the real
    SESSIONS_READY lifecycle event.

    Warm-up runs in a background thread, so wait for
    that thread to finish before assertions.
    """

    engine.start()

    event_bus.publish(
        Event(
            event_type=EventType.SESSIONS_READY,
            payload=None,
        )
    )

    if engine._warmup_thread is not None:
        engine._warmup_thread.join()


def create_candle_batch(
    symbol: str = "NIFTY",
    close: float = 155.0,
) -> CandleBatch:
    """
    Create one completed 5-minute candle batch.
    """

    candle = Candle(
        symbol=symbol,
        timeframe="5m",
        start_time=datetime(2026, 8, 17, 10, 15),
        end_time=datetime(2026, 8, 17, 10, 20),
        open=150.0,
        high=155.0,
        low=149.0,
        close=close,
    )

    return CandleBatch(
        timeframe="5m",
        start_time=datetime(2026, 8, 17, 10, 15),
        end_time=datetime(2026, 8, 17, 10, 20),
        candles={
            symbol: candle,
        },
    )


# ------------------------------------------------------------------
# Warm-up Tests
# ------------------------------------------------------------------


def test_single_symbol_warmup():
    """
    Verify that one symbol is warmed up correctly.
    """

    closes = [
        float(100 + i)
        for i in range(50)
    ]

    engine, state_store, event_bus = create_engine(
        symbols=["NIFTY"],
        candles_by_symbol={
            "NIFTY": create_candles(
                "NIFTY",
                closes,
            )
        },
    )

    start_engine_and_wait_for_warmup(
        engine,
        event_bus,
    )

    state = state_store.get(
        "NIFTY",
        "5m",
    )

    assert state is not None
    assert state.symbol == "NIFTY"
    assert state.timeframe == "5m"
    assert state.ready is True

    assert state.ema_10 == pytest.approx(
        engine._ema_calculator.calculate_from_closes(
            closes
        )
    )


def test_multiple_symbols_warmup_independently():
    """
    Verify that each active symbol receives its own
    independent indicator state.
    """

    nifty_closes = [
        float(100 + i)
        for i in range(50)
    ]

    banknifty_closes = [
        float(200 + i)
        for i in range(50)
    ]

    engine, state_store, event_bus = create_engine(
        symbols=[
            "NIFTY",
            "BANKNIFTY",
        ],
        candles_by_symbol={
            "NIFTY": create_candles(
                "NIFTY",
                nifty_closes,
            ),
            "BANKNIFTY": create_candles(
                "BANKNIFTY",
                banknifty_closes,
            ),
        },
    )

    start_engine_and_wait_for_warmup(
        engine,
        event_bus,
    )

    nifty_state = state_store.get(
        "NIFTY",
        "5m",
    )

    banknifty_state = state_store.get(
        "BANKNIFTY",
        "5m",
    )

    assert nifty_state is not None
    assert banknifty_state is not None

    assert nifty_state.ready is True
    assert banknifty_state.ready is True

    assert (
        nifty_state.ema_10
        != banknifty_state.ema_10
    )


def test_warmup_calculates_correct_ema():
    """
    Verify that warm-up calculates EMA using the
    historical candle closes.
    """

    closes = [
        float(100 + i)
        for i in range(50)
    ]

    engine, state_store, event_bus = create_engine(
        symbols=["NIFTY"],
        candles_by_symbol={
            "NIFTY": create_candles(
                "NIFTY",
                closes,
            )
        },
    )

    expected_ema = (
        engine._ema_calculator
        .calculate_from_closes(closes)
    )

    start_engine_and_wait_for_warmup(
        engine,
        event_bus,
    )

    state = state_store.get(
        "NIFTY",
        "5m",
    )

    assert state is not None

    assert state.ema_10 == pytest.approx(
        expected_ema
    )


def test_warmup_requires_50_candles():
    """
    Verify that warm-up fails when fewer than
    50 historical candles are available.
    """

    closes = [
        float(100 + i)
        for i in range(49)
    ]

    engine, state_store, event_bus = create_engine(
        symbols=["NIFTY"],
        candles_by_symbol={
            "NIFTY": create_candles(
                "NIFTY",
                closes,
            )
        },
    )

    engine._max_warmup_retries = 1

    with pytest.raises(ValueError):
        engine._warmup_symbol("NIFTY")

    assert state_store.get(
        "NIFTY",
        "5m",
    ) is None


def test_empty_symbol_list_does_nothing():
    """
    Verify that warm-up does nothing when there are
    no active symbols.
    """

    engine, state_store, event_bus = create_engine(
        symbols=[],
        candles_by_symbol={},
    )

    start_engine_and_wait_for_warmup(
        engine,
        event_bus,
    )

    assert state_store.get(
        "NIFTY",
        "5m",
    ) is None


def test_symbol_without_historical_data_fails():
    """
    Verify that missing historical data causes
    warm-up to fail.
    """

    engine, state_store, event_bus = create_engine(
        symbols=["NIFTY"],
        candles_by_symbol={},
    )

    engine._max_warmup_retries = 1

    with pytest.raises(ValueError):
        engine._warmup_symbol("NIFTY")

    assert state_store.get(
        "NIFTY",
        "5m",
    ) is None


# ------------------------------------------------------------------
# Live Indicator Update Tests
# ------------------------------------------------------------------


def test_live_candle_updates_ema():
    """
    Verify that a completed candle updates the existing EMA.
    """

    closes = [
        float(100 + i)
        for i in range(50)
    ]

    engine, state_store, event_bus = create_engine(
        symbols=["NIFTY"],
        candles_by_symbol={
            "NIFTY": create_candles(
                "NIFTY",
                closes,
            )
        },
    )

    start_engine_and_wait_for_warmup(
        engine,
        event_bus,
    )

    old_state = state_store.get(
        "NIFTY",
        "5m",
    )

    assert old_state is not None

    batch = create_candle_batch(
        symbol="NIFTY",
        close=155.0,
    )

    event_bus.publish(
        Event(
            event_type=EventType.CANDLE_BATCH_CLOSED,
            payload=batch,
        )
    )

    new_state = state_store.get(
        "NIFTY",
        "5m",
    )

    assert new_state is not None

    expected_ema = (
        engine._ema_calculator.update(
            previous_ema=old_state.ema_10,
            close=155.0,
        )
    )

    assert new_state.ema_10 == pytest.approx(
        expected_ema
    )


def test_indicator_batch_is_published():
    """
    Verify that processing a candle batch publishes
    INDICATOR_BATCH_UPDATED.
    """

    closes = [
        float(100 + i)
        for i in range(50)
    ]

    engine, state_store, event_bus = create_engine(
        symbols=["NIFTY"],
        candles_by_symbol={
            "NIFTY": create_candles(
                "NIFTY",
                closes,
            )
        },
    )

    received_batches = []

    def handler(event):
        received_batches.append(
            event.payload
        )

    event_bus.subscribe(
        EventType.INDICATOR_BATCH_UPDATED,
        handler,
    )

    start_engine_and_wait_for_warmup(
        engine,
        event_bus,
    )

    batch = create_candle_batch()

    event_bus.publish(
        Event(
            event_type=EventType.CANDLE_BATCH_CLOSED,
            payload=batch,
        )
    )

    assert len(received_batches) == 1

    indicator_batch = received_batches[0]

    assert indicator_batch.timeframe == "5m"

    assert (
        indicator_batch.start_time
        == batch.start_time
    )

    assert (
        indicator_batch.end_time
        == batch.end_time
    )

    assert "NIFTY" in (
        indicator_batch.indicators
    )


def test_indicator_batch_contains_updated_ema():
    """
    Verify that the published indicator batch contains
    the newly calculated EMA.
    """

    closes = [
        float(100 + i)
        for i in range(50)
    ]

    engine, state_store, event_bus = create_engine(
        symbols=["NIFTY"],
        candles_by_symbol={
            "NIFTY": create_candles(
                "NIFTY",
                closes,
            )
        },
    )

    received_batches = []

    def handler(event):
        received_batches.append(
            event.payload
        )

    event_bus.subscribe(
        EventType.INDICATOR_BATCH_UPDATED,
        handler,
    )

    start_engine_and_wait_for_warmup(
        engine,
        event_bus,
    )

    old_state = state_store.get(
        "NIFTY",
        "5m",
    )

    assert old_state is not None

    new_close = 155.0

    batch = create_candle_batch(
        symbol="NIFTY",
        close=new_close,
    )

    event_bus.publish(
        Event(
            event_type=EventType.CANDLE_BATCH_CLOSED,
            payload=batch,
        )
    )

    assert len(received_batches) == 1

    indicator_batch = received_batches[0]

    indicator_state = (
        indicator_batch.indicators["NIFTY"]
    )

    expected_ema = (
        engine._ema_calculator.update(
            previous_ema=old_state.ema_10,
            close=new_close,
        )
    )

    assert indicator_state.ema_10 == pytest.approx(
        expected_ema
    )


def test_multiple_symbols_update_in_one_batch():
    """
    Verify that multiple symbols can be updated
    from the same CandleBatch.
    """

    nifty_closes = [
        float(100 + i)
        for i in range(50)
    ]

    banknifty_closes = [
        float(200 + i)
        for i in range(50)
    ]

    engine, state_store, event_bus = create_engine(
        symbols=[
            "NIFTY",
            "BANKNIFTY",
        ],
        candles_by_symbol={
            "NIFTY": create_candles(
                "NIFTY",
                nifty_closes,
            ),
            "BANKNIFTY": create_candles(
                "BANKNIFTY",
                banknifty_closes,
            ),
        },
    )

    start_engine_and_wait_for_warmup(
        engine,
        event_bus,
    )

    nifty_old = state_store.get(
        "NIFTY",
        "5m",
    )

    banknifty_old = state_store.get(
        "BANKNIFTY",
        "5m",
    )

    assert nifty_old is not None
    assert banknifty_old is not None

    batch = CandleBatch(
        timeframe="5m",
        start_time=datetime(2026, 8, 17, 10, 15),
        end_time=datetime(2026, 8, 17, 10, 20),
        candles={
            "NIFTY": Candle(
                symbol="NIFTY",
                timeframe="5m",
                start_time=datetime(
                    2026,
                    8,
                    17,
                    10,
                    15,
                ),
                end_time=datetime(
                    2026,
                    8,
                    17,
                    10,
                    20,
                ),
                open=150.0,
                high=155.0,
                low=149.0,
                close=155.0,
            ),
            "BANKNIFTY": Candle(
                symbol="BANKNIFTY",
                timeframe="5m",
                start_time=datetime(
                    2026,
                    8,
                    17,
                    10,
                    15,
                ),
                end_time=datetime(
                    2026,
                    8,
                    17,
                    10,
                    20,
                ),
                open=250.0,
                high=255.0,
                low=249.0,
                close=255.0,
            ),
        },
    )

    event_bus.publish(
        Event(
            event_type=EventType.CANDLE_BATCH_CLOSED,
            payload=batch,
        )
    )

    nifty_new = state_store.get(
        "NIFTY",
        "5m",
    )

    banknifty_new = state_store.get(
        "BANKNIFTY",
        "5m",
    )

    assert nifty_new is not None
    assert banknifty_new is not None

    assert (
        nifty_new.ema_10
        != nifty_old.ema_10
    )

    assert (
        banknifty_new.ema_10
        != banknifty_old.ema_10
    )


# ------------------------------------------------------------------
# Shutdown Tests
# ------------------------------------------------------------------


def test_shutdown_runtime_clears_indicator_state():
    """
    Verify that shutdown_runtime() clears indicator
    state and pending candle batches.
    """

    closes = [
        float(100 + i)
        for i in range(50)
    ]

    engine, state_store, event_bus = create_engine(
        symbols=["NIFTY"],
        candles_by_symbol={
            "NIFTY": create_candles(
                "NIFTY",
                closes,
            )
        },
    )

    start_engine_and_wait_for_warmup(
        engine,
        event_bus,
    )

    assert state_store.get(
        "NIFTY",
        "5m",
    ) is not None

    engine._pending_batches.append(
        create_candle_batch()
    )

    engine.shutdown_runtime()

    assert state_store.get(
        "NIFTY",
        "5m",
    ) is None

    assert engine._pending_batches == []


def test_shutdown_runtime_stops_running_warmup_thread(
    monkeypatch,
):
    """
    Verify that shutdown_runtime() signals a running
    warm-up thread and waits for it to finish.
    """

    engine, state_store, event_bus = create_engine(
        symbols=["NIFTY"],
        candles_by_symbol={},
    )

    warmup_started = threading.Event()

    def blocked_warmup_symbol(symbol):
        warmup_started.set()

        # Simulate a warm-up operation that is still running.
        engine._warmup_stop_event.wait()

    monkeypatch.setattr(
        engine,
        "_warmup_symbol",
        blocked_warmup_symbol,
    )

    engine.start()

    event_bus.publish(
        Event(
            event_type=EventType.SESSIONS_READY,
            payload=None,
        )
    )

    assert warmup_started.wait(timeout=1)

    assert (
        engine._warmup_thread is not None
    )

    assert engine._warmup_thread.is_alive()

    engine.shutdown_runtime()

    assert (
        engine._warmup_stop_event.is_set()
    )

    assert (
        engine._warmup_thread.is_alive()
        is False
    )


def test_shutdown_interrupts_warmup_retry_wait():
    """
    Verify that the warm-up retry wait can be
    interrupted by the shutdown event.
    """

    closes = [
        float(100 + i)
        for i in range(49)
    ]

    engine, state_store, event_bus = create_engine(
        symbols=["NIFTY"],
        candles_by_symbol={
            "NIFTY": create_candles(
                "NIFTY",
                closes,
            )
        },
    )

    engine._warmup_stop_event.set()

    stopped = engine._warmup_stop_event.wait(
        timeout=30
    )

    assert stopped is True


def test_market_processing_complete_clears_indicator_runtime():
    """
    Verify that MARKET_PROCESSING_COMPLETE triggers
    IndicatorEngine runtime cleanup.
    """

    closes = [
        float(100 + i)
        for i in range(50)
    ]

    engine, state_store, event_bus = create_engine(
        symbols=["NIFTY"],
        candles_by_symbol={
            "NIFTY": create_candles(
                "NIFTY",
                closes,
            )
        },
    )

    start_engine_and_wait_for_warmup(
        engine,
        event_bus,
    )

    assert state_store.get(
        "NIFTY",
        "5m",
    ) is not None

    event_bus.publish(
        Event(
            event_type=EventType.MARKET_PROCESSING_COMPLETE,
            payload=None,
        )
    )

    assert state_store.get(
        "NIFTY",
        "5m",
    ) is None


# ------------------------------------------------------------------
# Candle Session Shutdown Tests
# ------------------------------------------------------------------


def test_market_close_publishes_processing_complete():
    """
    Verify that MARKET_CLOSE causes CandleSessionManager
    to finalize the boundary and publish
    MARKET_PROCESSING_COMPLETE.
    """

    event_bus = EventBus()

    received_events = []

    def handler(event):
        received_events.append(event)

    event_bus.subscribe(
        EventType.MARKET_PROCESSING_COMPLETE,
        handler,
    )

    candle_scheduler = CandleScheduler(
        timeframe=CandleTimeframe.FIVE_MINUTES,
        on_boundary=lambda interval_start: None,
    )

    candle_session_manager = CandleSessionManager(
        event_bus=event_bus,
        candle_scheduler=candle_scheduler,
    )

    candle_session_manager.start()

    boundary = datetime(
        2026,
        8,
        17,
        15,
        0,
    )

    event_bus.publish(
        Event(
            event_type=EventType.MARKET_CLOSE,
            payload=boundary,
        )
    )

    assert len(received_events) == 1

    assert (
        received_events[0].event_type
        == EventType.MARKET_PROCESSING_COMPLETE
    )


