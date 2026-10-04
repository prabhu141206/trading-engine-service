from datetime import datetime

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

    # Create the EventBus used for internal event communication.
    event_bus = EventBus()

    # Create the runtime registry containing symbols that need
    # market-data subscriptions.
    registry = SubscriptionRegistry()

    # Create a fake WebSocket so that no real broker connection
    # is required during the test.
    websocket = FakeWebSocketClient()

    # Create the MarketDataManager with its required dependencies.
    manager = MarketDataManager(
        event_bus=event_bus,
        subscription_registry=registry,
        websocket_client=websocket,
    )

    # Store ticks received through the TICK_RECEIVED event.
    received_ticks = []

    def handler(event):
        """Collect the tick carried by the received event."""
        received_ticks.append(event.payload)

    # Subscribe the test handler to TICK_RECEIVED events.
    event_bus.subscribe(
        EventType.TICK_RECEIVED,
        handler,
    )

    # Register NIFTY as a symbol that requires market-data subscription.
    registry.add_symbol("NIFTY")

    # Start the MarketDataManager.
    manager.start()

    # Notify MarketDataManager that the runtime sessions and
    # subscription registry are ready.
    event_bus.publish(
        Event(
            EventType.SESSIONS_READY,
            None,
        )
    )

    # Verify that MarketDataManager subscribed the WebSocket
    # to the symbol present in the SubscriptionRegistry.
    assert websocket.subscribed == {"NIFTY"}

    # Create a simulated market tick.
    tick = Tick(
        symbol="NIFTY",
        price=25100.5,
        timestamp=datetime.now(),
    )

    # Simulate the WebSocket receiving the tick.
    websocket.emit_tick(tick)

    # Verify that exactly one TICK_RECEIVED event was published
    # and that it contains the expected NIFTY tick.
    assert len(received_ticks) == 1
    assert received_ticks[0].symbol == "NIFTY"




def test_tick_is_published_when_accepting_ticks():
    """
    Test Case:
    Verify that MarketDataManager publishes a TICK_RECEIVED event
    when tick processing is enabled.

    Expected flow:

        MarketDataManager
                ↓
        _on_tick()
                ↓
        TICK_RECEIVED
                ↓
            EventBus
                ↓
        Test handler
    """

    # Create the EventBus used for internal event communication.
    event_bus = EventBus()

    # Create the subscription registry required by
    # MarketDataManager.
    registry = SubscriptionRegistry()

    # Create a fake WebSocket client so no real broker
    # connection is required.
    websocket = FakeWebSocketClient()

    # Create the MarketDataManager.
    manager = MarketDataManager(
        event_bus=event_bus,
        subscription_registry=registry,
        websocket_client=websocket,
    )

    # Store ticks received from the EventBus.
    received_ticks = []

    def handler(event):
        """Store the tick received through TICK_RECEIVED."""
        received_ticks.append(event.payload)

    # Subscribe the test handler.
    event_bus.subscribe(
        EventType.TICK_RECEIVED,
        handler,
    )

    # Enable tick processing.
    manager._accepting_ticks = True

    # Create a simulated market tick.
    tick = Tick(
        symbol="NIFTY",
        price=25100.5,
        timestamp=datetime.now(),
    )

    # Send the tick directly to MarketDataManager.
    manager._on_tick(tick)

    # Verify that the tick was published.
    assert len(received_ticks) == 1
    assert received_ticks[0] is tick


def test_tick_is_ignored_after_market_close():
    """
    Test Case:
    Verify that MarketDataManager stops publishing ticks
    after MARKET_CLOSE.

    Expected flow:

        MARKET_CLOSE
             ↓
        _accepting_ticks = False
             ↓
        Incoming Tick
             ↓
        _on_tick()
             ↓
        No TICK_RECEIVED event
    """

    # Create the EventBus used for internal event communication.
    event_bus = EventBus()

    # Create the subscription registry.
    registry = SubscriptionRegistry()

    # Create a fake WebSocket client.
    websocket = FakeWebSocketClient()

    # Create the MarketDataManager.
    manager = MarketDataManager(
        event_bus=event_bus,
        subscription_registry=registry,
        websocket_client=websocket,
    )

    # Store any ticks that are published.
    received_ticks = []

    def handler(event):
        """Store ticks received through TICK_RECEIVED."""
        received_ticks.append(event.payload)

    # Subscribe the test handler.
    event_bus.subscribe(
        EventType.TICK_RECEIVED,
        handler,
    )

    # Start with tick processing enabled.
    manager._accepting_ticks = True

    # Simulate market close.
    manager._on_market_close(
        Event(
            event_type=EventType.MARKET_CLOSE,
            payload=None,
        )
    )

    # Create a tick that arrives after market close.
    tick = Tick(
        symbol="NIFTY",
        price=25100.5,
        timestamp=datetime.now(),
    )

    # Simulate a late tick.
    manager._on_tick(tick)

    # Verify that the late tick was not published.
    assert len(received_ticks) == 0



def test_market_processing_complete_disconnects_websocket():
    """
    Test Case:
    Verify that MarketDataManager disconnects the WebSocket
    after all market processing has completed.

    Expected flow:

        MARKET_PROCESSING_COMPLETE
                ↓
        unsubscribe symbols
                ↓
        disconnect WebSocket
                ↓
        clear subscribed symbols
    """

    # Create the EventBus used for internal event communication.
    event_bus = EventBus()

    # Create the subscription registry.
    registry = SubscriptionRegistry()

    # Create the fake WebSocket client.
    websocket = FakeWebSocketClient()

    # Register a symbol that requires market-data subscription.
    registry.add_symbol("NIFTY")

    # Create the MarketDataManager.
    manager = MarketDataManager(
        event_bus=event_bus,
        subscription_registry=registry,
        websocket_client=websocket,
    )

    # Start the MarketDataManager.
    manager.start()

    # Simulate runtime sessions becoming ready.
    event_bus.publish(
        Event(
            event_type=EventType.SESSIONS_READY,
            payload=None,
        )
    )

    # Verify that the WebSocket connected.
    assert websocket.connected is True

    # Verify that NIFTY was subscribed.
    assert websocket.subscribed == {"NIFTY"}

    # Simulate completion of all market processing.
    event_bus.publish(
        Event(
            event_type=EventType.MARKET_PROCESSING_COMPLETE,
            payload=None,
        )
    )

    # WebSocket must now be disconnected.
    assert websocket.connected is False

    # Active WebSocket subscriptions must be cleared.
    assert websocket.subscribed == set()

    # MarketDataManager's own subscription tracking
    # must also be cleared.
    assert manager._subscribed_symbols == set()