from datetime import datetime

from event_system.event import Event
from event_system.event_bus import EventBus
from event_system.event_type import EventType
from market_data.models import Tick
from tick_cache.tick_cache import TickCache


def publish_tick(event_bus, symbol, price):
    """
    Publish a simulated TICK_RECEIVED event.

    This helper creates a Tick object and publishes it through
    the EventBus so that TickCache receives it through its
    normal event-driven flow.

    Returns:
        Tick: The tick that was published.
    """
    tick = Tick(
        symbol=symbol,
        price=price,
        timestamp=datetime.now(),
    )

    event_bus.publish(
        Event(
            event_type=EventType.TICK_RECEIVED,
            payload=tick,
        )
    )

    return tick


def test_update_latest_tick():
    """
    Test Case:
    Verify that TickCache stores the latest tick received for
    a symbol.

    Expected Result:
    After publishing a NIFTY tick, get_latest("NIFTY") should
    return the same tick.
    """

    # Create the EventBus used to deliver market-data events.
    event_bus = EventBus()

    # Create and start the TickCache so that it begins listening
    # for TICK_RECEIVED events.
    cache = TickCache(event_bus)
    cache.start()

    # Publish a NIFTY tick through the normal event flow.
    tick = publish_tick(
        event_bus,
        "NIFTY",
        25100.5,
    )

    # Verify that the published tick is stored as the latest
    # tick for NIFTY.
    assert cache.get_latest("NIFTY") == tick


def test_replace_existing_tick():
    """
    Test Case:
    Verify that a new tick replaces the previously cached tick
    for the same symbol.

    Expected Result:
    The cache should return the most recently received NIFTY tick.
    """

    # Create and start the TickCache.
    event_bus = EventBus()
    cache = TickCache(event_bus)
    cache.start()

    # Publish the first NIFTY tick.
    publish_tick(
        event_bus,
        "NIFTY",
        25100.5,
    )

    # Publish a newer NIFTY tick.
    latest = publish_tick(
        event_bus,
        "NIFTY",
        25105.0,
    )

    # Verify that the newer tick has replaced the previous tick.
    assert cache.get_latest("NIFTY") == latest
    assert cache.get_latest("NIFTY").price == 25105.0


def test_unknown_symbol_returns_none():
    """
    Test Case:
    Verify that requesting the latest tick for a symbol that has
    never been cached returns None.

    Expected Result:
    get_latest() should return None for an unknown symbol.
    """

    # Create and start an empty TickCache.
    event_bus = EventBus()
    cache = TickCache(event_bus)
    cache.start()

    # BANKNIFTY has not received any tick yet.
    assert cache.get_latest("BANKNIFTY") is None


def test_clear_cache():
    """
    Test Case:
    Verify that clear() removes all cached ticks.

    Expected Result:
    After clearing the cache, no previously cached symbol
    should have a latest tick.
    """

    # Create and start the TickCache.
    event_bus = EventBus()
    cache = TickCache(event_bus)
    cache.start()

    # Add ticks for multiple symbols.
    publish_tick(
        event_bus,
        "NIFTY",
        25100.5,
    )

    publish_tick(
        event_bus,
        "BANKNIFTY",
        56000.0,
    )

    # Clear all cached ticks.
    cache.clear()

    # Verify that both symbols have been removed from the cache.
    assert cache.get_latest("NIFTY") is None
    assert cache.get_latest("BANKNIFTY") is None


def test_has_symbol():
    """
    Test Case:
    Verify that has_symbol() correctly reports whether a symbol
    has a cached tick.

    Expected Result:
    The method should return False before a tick is received
    and True after a tick for that symbol is cached.
    """

    # Create and start the TickCache.
    event_bus = EventBus()
    cache = TickCache(event_bus)
    cache.start()

    # NIFTY has not received a tick yet, so it should not exist
    # in the cache.
    assert cache.has_symbol("NIFTY") is False

    # Publish a NIFTY tick.
    publish_tick(
        event_bus,
        "NIFTY",
        25100.5,
    )

    # NIFTY should now exist in the cache.
    assert cache.has_symbol("NIFTY") is True