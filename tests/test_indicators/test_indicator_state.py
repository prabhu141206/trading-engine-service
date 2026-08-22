from indicators.indicator_models import SymbolIndicatorState
from indicators.indicator_state import IndicatorStateStore


def test_store_and_get_indicator_state():

    store = IndicatorStateStore()

    state = SymbolIndicatorState(
        symbol="NIFTY",
        timeframe="5m",
        ema_10=25102.35,
    )

    store.set(state)

    result = store.get(
        "NIFTY",
        "5m",
    )

    assert result == state


def test_get_unknown_symbol_returns_none():

    store = IndicatorStateStore()

    result = store.get(
        "NIFTY",
        "5m",
    )

    assert result is None


def test_multiple_symbols_have_independent_state():

    store = IndicatorStateStore()

    nifty = SymbolIndicatorState(
        symbol="NIFTY",
        timeframe="5m",
        ema_10=25102.35,
    )

    banknifty = SymbolIndicatorState(
        symbol="BANKNIFTY",
        timeframe="5m",
        ema_10=55120.72,
    )

    store.set(nifty)
    store.set(banknifty)

    assert store.get("NIFTY", "5m") == nifty
    assert store.get("BANKNIFTY", "5m") == banknifty


def test_set_updates_existing_state():

    store = IndicatorStateStore()

    old_state = SymbolIndicatorState(
        symbol="NIFTY",
        timeframe="5m",
        ema_10=25100.0,
    )

    new_state = SymbolIndicatorState(
        symbol="NIFTY",
        timeframe="5m",
        ema_10=25110.0,
    )

    store.set(old_state)
    store.set(new_state)

    assert store.get(
        "NIFTY",
        "5m",
    ) == new_state


def test_is_ready():

    store = IndicatorStateStore()

    state = SymbolIndicatorState(
        symbol="NIFTY",
        timeframe="5m",
        ema_10=25102.35,
        ready=True,
    )

    store.set(state)

    assert store.is_ready(
        "NIFTY",
        "5m",
    )


def test_unknown_symbol_is_not_ready():

    store = IndicatorStateStore()

    assert not store.is_ready(
        "NIFTY",
        "5m",
    )


def test_remove_state():

    store = IndicatorStateStore()

    state = SymbolIndicatorState(
        symbol="NIFTY",
        timeframe="5m",
        ema_10=25102.35,
    )

    store.set(state)

    store.remove(
        "NIFTY",
        "5m",
    )

    assert store.get(
        "NIFTY",
        "5m",
    ) is None