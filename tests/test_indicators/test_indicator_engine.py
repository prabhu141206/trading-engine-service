import pytest

from datetime import datetime

from candle.candle_models import Candle, CandleBatch

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


def create_candles(
    symbol: str,
    closes: list[float],
) -> list[Candle]:

    candles = []

    for index, close in enumerate(closes):

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
    # Create a separate EventBus for every test.
    # This keeps events from different tests isolated.
    event_bus = EventBus()

    # FakeActiveSymbolProvider represents the symbols that
    # would normally come from the runtime SubscriptionRegistry.
    symbol_provider = FakeActiveSymbolProvider(
        symbols
    )

    # FakeHistoricalCandleProvider provides historical candles
    # without making a real Angel One API request.
    historical_provider = FakeHistoricalCandleProvider(
        candles_by_symbol
    )

    # IndicatorStateStore keeps the latest EMA state
    # for every symbol and timeframe.
    state_store = IndicatorStateStore()

    # Create the IndicatorEngine with all required dependencies.
    engine = IndicatorEngine(
        event_bus=event_bus,
        symbol_provider=symbol_provider,
        historical_provider=historical_provider,
        state_store=state_store,
    )

    return engine, state_store, event_bus


def start_engine(
    engine: IndicatorEngine,
    event_bus: EventBus,
) -> None:
    """
    Start the IndicatorEngine using the same lifecycle
    that the real application will use.

    engine.start()
        -> registers event subscriptions

    SESSIONS_READY
        -> tells IndicatorEngine that the runtime configuration
           is ready and historical warmup can begin.
    """

    # Start listening for events.
    engine.start()

    # Simulate the application telling the IndicatorEngine
    # that all active sessions/configuration are ready.
    event_bus.publish(
        Event(
            event_type=EventType.SESSIONS_READY,
        )
    )


def test_single_symbol_warmup():

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

    # Start the engine and trigger historical warmup.
    start_engine(engine, event_bus)

    state = state_store.get(
        "NIFTY",
        "5m",
    )

    # Verify that the EMA state was created.
    assert state is not None

    # Verify the basic state information.
    assert state.symbol == "NIFTY"
    assert state.timeframe == "5m"
    assert state.ready is True

    # Verify that the calculated EMA is correct.
    assert state.ema_10 == pytest.approx(
        engine._ema_calculator.calculate_from_closes(
            closes
        )
    )


def test_multiple_symbols_warmup_independently():

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

    # Warm up both active symbols.
    start_engine(engine, event_bus)

    nifty_state = state_store.get(
        "NIFTY",
        "5m",
    )

    banknifty_state = state_store.get(
        "BANKNIFTY",
        "5m",
    )

    # Both symbols must have an initialized indicator state.
    assert nifty_state is not None
    assert banknifty_state is not None

    assert nifty_state.ready is True
    assert banknifty_state.ready is True

    # Different price series should produce different EMA values.
    assert nifty_state.ema_10 != banknifty_state.ema_10


def test_warmup_calculates_correct_ema():

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

    # Calculate the expected EMA independently.
    expected_ema = (
        engine._ema_calculator
        .calculate_from_closes(closes)
    )

    # Trigger the real warmup lifecycle.
    start_engine(engine, event_bus)

    state = state_store.get(
        "NIFTY",
        "5m",
    )

    assert state is not None

    # The stored EMA must match the calculated EMA.
    assert state.ema_10 == pytest.approx(
        expected_ema
    )


def test_warmup_requires_50_candles():

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

    # Warmup is triggered by SESSIONS_READY.
    #
    # Only 49 candles are available, while the IndicatorEngine
    # requires 50 candles. EventBus catches the ValueError raised
    # by the IndicatorEngine, so pytest.raises() cannot be used here.
    start_engine(engine, event_bus)

    # Because warmup failed, no indicator state should exist.
    assert state_store.get(
        "NIFTY",
        "5m",
    ) is None


def test_empty_symbol_list_does_nothing():

    engine, state_store, event_bus = create_engine(
        symbols=[],
        candles_by_symbol={},
    )

    # Start the engine normally.
    # There are no active symbols, so there is nothing to warm up.
    start_engine(engine, event_bus)

    # Verify that no state was created for a symbol.
    assert state_store.get(
        "NIFTY",
        "5m",
    ) is None


def test_symbol_without_historical_data_fails():

    engine, state_store, event_bus = create_engine(
        symbols=["NIFTY"],
        candles_by_symbol={},
    )

    # NIFTY is an active symbol, but the historical provider
    # returned zero candles.
    #
    # The IndicatorEngine raises ValueError internally, but
    # EventBus catches subscriber exceptions. Therefore this test
    # verifies the observable result: no indicator state is created.
    start_engine(engine, event_bus)

    # Warmup failed, so NIFTY must not have an initialized state.
    assert state_store.get(
        "NIFTY",
        "5m",
    ) is None


def test_live_candle_updates_ema():

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

    # First perform the historical warmup.
    # Live candles can only be processed after
    # an initial EMA state exists.
    start_engine(engine, event_bus)

    old_state = state_store.get(
        "NIFTY",
        "5m",
    )

    assert old_state is not None

    new_candle = Candle(
        symbol="NIFTY",
        timeframe="5m",
        start_time=datetime(2026, 8, 17, 10, 15),
        end_time=datetime(2026, 8, 17, 10, 20),
        open=150.0,
        high=155.0,
        low=149.0,
        close=155.0,
    )

    batch = CandleBatch(
        timeframe="5m",
        start_time=datetime(2026, 8, 17, 10, 15),
        end_time=datetime(2026, 8, 17, 10, 20),
        candles={
            "NIFTY": new_candle,
        },
    )

    # Send the completed candle batch to the IndicatorEngine.
    # The engine should update the existing EMA.
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

    # Calculate what the updated EMA should be.
    expected_ema = engine._ema_calculator.update(
        previous_ema=old_state.ema_10,
        close=155.0,
    )

    assert new_state.ema_10 == pytest.approx(
        expected_ema
    )


def test_indicator_batch_is_published():

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
        # Store the IndicatorBatch published by IndicatorEngine.
        received_batches.append(
            event.payload
        )

    event_bus.subscribe(
        EventType.INDICATOR_BATCH_UPDATED,
        handler,
    )

    # Perform historical warmup before sending live data.
    start_engine(engine, event_bus)

    candle = Candle(
        symbol="NIFTY",
        timeframe="5m",
        start_time=datetime(2026, 8, 17, 10, 15),
        end_time=datetime(2026, 8, 17, 10, 20),
        open=150.0,
        high=155.0,
        low=149.0,
        close=155.0,
    )

    batch = CandleBatch(
        timeframe="5m",
        start_time=datetime(2026, 8, 17, 10, 15),
        end_time=datetime(2026, 8, 17, 10, 20),
        candles={
            "NIFTY": candle,
        },
    )

    # A completed candle should cause the IndicatorEngine
    # to publish an updated IndicatorBatch.
    event_bus.publish(
        Event(
            event_type=EventType.CANDLE_BATCH_CLOSED,
            payload=batch,
        )
    )

    # Exactly one indicator batch should have been published.
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

    # The batch must contain the updated NIFTY indicator state.
    assert "NIFTY" in indicator_batch.indicators


def test_indicator_batch_contains_updated_ema():

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
        # Capture every IndicatorBatch published by the engine.
        received_batches.append(
            event.payload
        )

    event_bus.subscribe(
        EventType.INDICATOR_BATCH_UPDATED,
        handler,
    )

    # Warm up the EMA before processing a live candle.
    start_engine(engine, event_bus)

    old_state = state_store.get(
        "NIFTY",
        "5m",
    )

    assert old_state is not None

    new_close = 155.0

    candle = Candle(
        symbol="NIFTY",
        timeframe="5m",
        start_time=datetime(2026, 8, 17, 10, 15),
        end_time=datetime(2026, 8, 17, 10, 20),
        open=150.0,
        high=155.0,
        low=149.0,
        close=new_close,
    )

    batch = CandleBatch(
        timeframe="5m",
        start_time=datetime(2026, 8, 17, 10, 15),
        end_time=datetime(2026, 8, 17, 10, 20),
        candles={
            "NIFTY": candle,
        },
    )

    # Process the completed candle.
    event_bus.publish(
        Event(
            event_type=EventType.CANDLE_BATCH_CLOSED,
            payload=batch,
        )
    )

    indicator_batch = received_batches[0]

    indicator_state = (
        indicator_batch.indicators["NIFTY"]
    )

    # Calculate the expected EMA after the new candle.
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

    # Warm up both symbols before processing live candles.
    start_engine(engine, event_bus)

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

    # Send one CandleBatch containing both symbols.
    # The IndicatorEngine should update both EMA states.
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

    # Verify that both symbols received a new EMA value.
    assert (
        nifty_new.ema_10
        != nifty_old.ema_10
    )

    assert (
        banknifty_new.ema_10
        != banknifty_old.ema_10
    )