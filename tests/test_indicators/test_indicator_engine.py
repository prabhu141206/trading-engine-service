import pytest

from candle.candle_models import Candle
from event_system.event_bus import EventBus
from indicators.fake_active_symbol_provider import (
    FakeActiveSymbolProvider,
)
from indicators.fake_historical_data_provider import (
    FakeHistoricalCandleProvider,
)
from indicators.indicator_engine import IndicatorEngine
from indicators.indicator_state import IndicatorStateStore

from datetime import datetime

from candle.candle_models import CandleBatch
from event_system.event import Event
from event_system.event_type import EventType

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

    engine.start()

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

    engine.start()

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

    assert nifty_state.ema_10 != (
        banknifty_state.ema_10
    )


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

    expected_ema = (
        engine._ema_calculator
        .calculate_from_closes(closes)
    )

    engine.start()

    state = state_store.get(
        "NIFTY",
        "5m",
    )

    assert state is not None

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

    with pytest.raises(ValueError):

        engine.start()

    assert state_store.get(
        "NIFTY",
        "5m",
    ) is None


def test_empty_symbol_list_does_nothing():

    engine, state_store, event_bus = create_engine(
        symbols=[],
        candles_by_symbol={},
    )

    engine.start()

    assert state_store.get(
        "NIFTY",
        "5m",
    ) is None


def test_symbol_without_historical_data_fails():

    engine, state_store, event_bus = create_engine(
        symbols=["NIFTY"],
        candles_by_symbol={},
    )

    with pytest.raises(ValueError):

        engine.start()

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

    engine.start()

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
        received_batches.append(
            event.payload
        )

    event_bus.subscribe(
        EventType.INDICATOR_BATCH_UPDATED,
        handler,
    )

    engine.start()

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

    engine.start()

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

    engine.start()

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
                    2026, 8, 17, 10, 15
                ),
                end_time=datetime(
                    2026, 8, 17, 10, 20
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
                    2026, 8, 17, 10, 15
                ),
                end_time=datetime(
                    2026, 8, 17, 10, 20
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