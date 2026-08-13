from datetime import datetime

from event_system.event import Event
from event_system.event_bus import EventBus
from event_system.event_type import EventType
from market_data.models import Tick
from tick_cache.tick_cache import TickCache


def publish_tick(event_bus, symbol, price):
    tick = Tick(
        symbol=symbol,
        price=price,
        timestamp=datetime.now()
    )

    event_bus.publish(
        Event(
            event_type=EventType.TICK_RECEIVED,
            payload=tick
        )
    )

    return tick


def test_update_latest_tick():

    event_bus = EventBus()
    cache = TickCache(event_bus)

    cache.start()

    tick = publish_tick(event_bus, "NIFTY", 25100.5)

    assert cache.get_latest("NIFTY") == tick


def test_replace_existing_tick():

    event_bus = EventBus()
    cache = TickCache(event_bus)

    cache.start()

    publish_tick(event_bus, "NIFTY", 25100.5)

    latest = publish_tick(event_bus, "NIFTY", 25105.0)

    assert cache.get_latest("NIFTY") == latest
    assert cache.get_latest("NIFTY").price == 25105.0


def test_unknown_symbol_returns_none():

    event_bus = EventBus()
    cache = TickCache(event_bus)

    cache.start()

    assert cache.get_latest("BANKNIFTY") is None


def test_clear_cache():

    event_bus = EventBus()
    cache = TickCache(event_bus)

    cache.start()

    publish_tick(event_bus, "NIFTY", 25100.5)
    publish_tick(event_bus, "BANKNIFTY", 56000.0)

    cache.clear()

    assert cache.get_latest("NIFTY") is None
    assert cache.get_latest("BANKNIFTY") is None


def test_has_symbol():

    event_bus = EventBus()
    cache = TickCache(event_bus)

    cache.start()

    assert cache.has_symbol("NIFTY") is False

    publish_tick(event_bus, "NIFTY", 25100.5)

    assert cache.has_symbol("NIFTY") is True