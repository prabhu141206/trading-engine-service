from datetime import datetime
from unittest.mock import Mock

from event_system import event_bus
from event_system.event import Event
from event_system.event_bus import EventBus
from event_system.event_type import EventType
from market_data.market_data_manager import MarketDataManager
from market_data.models import Tick
from registry.subscription_registry import SubscriptionRegistry


class FakeWebSocketClient:
    """
    Fake WebSocket client used for testing MarketDataManager.

    It simulates:
    - WebSocket connection
    - Symbol subscription/unsubscription
    - Tick handler registration
    - Incoming tick events

    No real WebSocket connection is required.
    """

    def __init__(self):
        self.connected = False
        self.subscribed = set()
        self.handler = None

    def connect(self):
        """Simulate establishing a WebSocket connection."""
        self.connected = True

    def disconnect(self):
        """Simulate closing the WebSocket connection."""
        self.connected = False

    def subscribe(self, symbols):
        """Simulate subscribing to market-data symbols."""
        self.subscribed.update(symbols)

    def unsubscribe(self, symbols):
        """Simulate unsubscribing from market-data symbols."""
        self.subscribed.difference_update(symbols)

    def set_tick_handler(self, handler):
        """Register the callback used when a tick is received."""
        self.handler = handler

    def emit_tick(self, tick):
        """
        Simulate receiving a tick from the WebSocket.

        The registered tick handler is called with the
        provided Tick object.
        """
        self.handler(tick)


def test_publish_tick_event():
    """
    Test Case:
    Verify that MarketDataManager subscribes to symbols from the
    SubscriptionRegistry and publishes received ticks through
    the EventBus.

    Expected flow:

        SubscriptionRegistry
                ↓
        MarketDataManager
                ↓
        WebSocket subscription
                ↓
        Incoming Tick
                ↓
        TICK_RECEIVED Event
                ↓
        EventBus subscriber
    """

    event_bus = EventBus()
    registry = SubscriptionRegistry()
    websocket = FakeWebSocketClient()
    system_monitor = Mock()

    manager = MarketDataManager(
        event_bus=event_bus,
        subscription_registry=registry,
        websocket_client=websocket,
        system_monitor=system_monitor,
    )

    received_ticks = []

    def handler(event):
        """Collect the tick carried by the received event."""
        received_ticks.append(event.payload)

    event_bus.subscribe(
        EventType.TICK_RECEIVED,
        handler,
    )

    registry.add_symbol("NIFTY")

    manager.start()

    event_bus.publish(
        Event(
            EventType.SESSIONS_READY,
            None,
        )
    )

    assert websocket.subscribed == {"NIFTY"}

    tick = Tick(
        symbol="NIFTY",
        price=25100.5,
        timestamp=datetime.now(),
    )

    websocket.emit_tick(tick)

    assert len(received_ticks) == 1
    assert received_ticks[0].symbol == "NIFTY"


def test_tick_is_published_when_accepting_ticks():
    """
    Test Case:
    Verify that MarketDataManager publishes a TICK_RECEIVED event
    when tick processing is enabled.
    """

    event_bus = EventBus()
    registry = SubscriptionRegistry()
    websocket = FakeWebSocketClient()
    system_monitor = Mock()

    manager = MarketDataManager(
        event_bus=event_bus,
        subscription_registry=registry,
        websocket_client=websocket,
        system_monitor=system_monitor,
    )

    received_ticks = []

    def handler(event):
        """Store the tick received through TICK_RECEIVED."""
        received_ticks.append(event.payload)

    event_bus.subscribe(
        EventType.TICK_RECEIVED,
        handler,
    )

    manager._accepting_ticks = True

    tick = Tick(
        symbol="NIFTY",
        price=25100.5,
        timestamp=datetime.now(),
    )

    manager._on_tick(tick)

    assert len(received_ticks) == 1
    assert received_ticks[0] is tick


def test_tick_is_ignored_after_market_close():
    """
    Test Case:
    Verify that MarketDataManager stops publishing ticks
    after MARKET_CLOSE.
    """

    event_bus = EventBus()
    registry = SubscriptionRegistry()
    websocket = FakeWebSocketClient()
    system_monitor = Mock()

    manager = MarketDataManager(
        event_bus=event_bus,
        subscription_registry=registry,
        websocket_client=websocket,
        system_monitor=system_monitor,
    )

    received_ticks = []

    def handler(event):
        """Store ticks received through TICK_RECEIVED."""
        received_ticks.append(event.payload)

    event_bus.subscribe(
        EventType.TICK_RECEIVED,
        handler,
    )

    manager._accepting_ticks = True

    manager._on_market_close(
        Event(
            event_type=EventType.MARKET_CLOSE,
            payload=None,
        )
    )

    tick = Tick(
        symbol="NIFTY",
        price=25100.5,
        timestamp=datetime.now(),
    )

    manager._on_tick(tick)

    assert len(received_ticks) == 0


def test_market_processing_complete_disconnects_websocket():
    """
    Test Case:
    Verify that MarketDataManager disconnects the WebSocket
    after all market processing has completed.
    """

    event_bus = EventBus()
    registry = SubscriptionRegistry()
    websocket = FakeWebSocketClient()
    system_monitor = Mock()

    registry.add_symbol("NIFTY")

    manager = MarketDataManager(
        event_bus=event_bus,
        subscription_registry=registry,
        websocket_client=websocket,
        system_monitor=system_monitor,
    )

    manager.start()

    event_bus.publish(
        Event(
            event_type=EventType.SESSIONS_READY,
            payload=None,
        )
    )

    assert websocket.connected is True
    assert websocket.subscribed == {"NIFTY"}

    event_bus.publish(
        Event(
            event_type=EventType.MARKET_PROCESSING_COMPLETE,
            payload=None,
        )
    )

    assert websocket.connected is False
    assert websocket.subscribed == set()
    assert manager._subscribed_symbols == set()