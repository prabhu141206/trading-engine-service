from datetime import datetime

from event_system.event import Event
from event_system.event_bus import EventBus
from event_system.event_type import EventType
from market_data.market_data_manager import MarketDataManager
from market_data.models import Tick
from registry.subscription_registry import SubscriptionRegistry


class FakeWebSocketClient:

    def __init__(self):
        self.connected = False
        self.subscribed = set()
        self.handler = None

    def connect(self):
        self.connected = True

    def disconnect(self):
        self.connected = False

    def subscribe(self, symbols):
        self.subscribed.update(symbols)

    def unsubscribe(self, symbols):
        self.subscribed.difference_update(symbols)

    def set_tick_handler(self, handler):
        self.handler = handler

    def emit_tick(self, tick):
        self.handler(tick)


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

    event_bus.subscribe(
        EventType.TICK_RECEIVED,
        handler
    )

    # Register the symbol in the new registry
    registry.add_symbol("NIFTY")

    manager.start()

    # Notify MarketDataManager that registry is ready
    event_bus.publish(
        Event(EventType.SESSIONS_READY, None)
    )

    # Verify websocket subscription
    assert websocket.subscribed == {"NIFTY"}

    tick = Tick(
        symbol="NIFTY",
        price=25100.5,
        timestamp=datetime.now()
    )

    websocket.emit_tick(tick)

    assert len(received_ticks) == 1
    assert received_ticks[0].symbol == "NIFTY"