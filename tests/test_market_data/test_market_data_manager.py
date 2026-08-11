from datetime import UTC, datetime

from event_system.event_type import EventType
from event_system.event_bus import EventBus
from market_data.market_data_manager import MarketDataManager
from market_data.tick import Tick
from market_data.websocket_client import FakeWebSocketClient
from session.user_session import UserSession
from subscription_registry.subscription_registry import SubscriptionRegistry


def test_sync_subscriptions():

    event_bus = EventBus()
    registry = SubscriptionRegistry()
    websocket = FakeWebSocketClient()

    registry.add_session(
        UserSession(
            user_id=101,
            subscribed_symbols={"NIFTY", "BANKNIFTY"}
        )
    )

    manager = MarketDataManager(
        event_bus=event_bus,
        subscription_registry=registry,
        websocket_client=websocket
    )

    manager.start()

    assert websocket.connected is True
    assert websocket.subscribed_symbols == {
        "NIFTY",
        "BANKNIFTY"
    }


def test_unsubscribe_removed_symbol():

    event_bus = EventBus()
    registry = SubscriptionRegistry()
    websocket = FakeWebSocketClient()

    registry.add_session(
        UserSession(
            user_id=101,
            subscribed_symbols={"NIFTY"}
        )
    )

    manager = MarketDataManager(
        event_bus=event_bus,
        subscription_registry=registry,
        websocket_client=websocket
    )

    manager.start()

    registry.remove_session(101)

    manager.sync_subscriptions()

    assert websocket.subscribed_symbols == set()


def test_publish_tick_event():

    event_bus = EventBus()
    registry = SubscriptionRegistry()
    websocket = FakeWebSocketClient()

    manager = MarketDataManager(
        event_bus=event_bus,
        subscription_registry=registry,
        websocket_client=websocket
    )

    received_ticks = []

    def handler(event):
        received_ticks.append(event.payload)

    event_bus.subscribe(EventType.TICK_RECEIVED, handler)

    manager.start()

    tick = Tick(
        symbol="NIFTY",
        price=25100.5,
        timestamp=datetime.now(UTC)
    )

    websocket.emit_tick(tick)

    assert len(received_ticks) == 1
    assert received_ticks[0].symbol == "NIFTY"