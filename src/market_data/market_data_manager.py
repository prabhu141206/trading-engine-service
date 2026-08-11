from event_system.event import Event
from event_system.event_bus import EventBus
from event_system.event_type import EventType

from market_data.tick import Tick
from market_data.websocket_client import FakeWebSocketClient
from subscription_registry.subscription_registry import SubscriptionRegistry


class MarketDataManager:
    """
    Shared market data manager.

    Responsibilities
    ----------------
    - Maintain one websocket connection.
    - Synchronize symbol subscriptions.
    - Receive ticks from websocket.
    - Publish ticks through EventBus.
    """

    def __init__(
        self,
        event_bus: EventBus,
        subscription_registry: SubscriptionRegistry,
        websocket_client: FakeWebSocketClient,
    ) -> None:

        self._event_bus = event_bus
        self._subscription_registry = subscription_registry
        self._websocket_client = websocket_client

        # Currently active websocket subscriptions.
        self._active_symbols: set[str] = set()

        # Register tick callback.
        self._websocket_client.set_tick_handler(self.on_tick)

    # ---------------------------------------------------------
    # Lifecycle
    # ---------------------------------------------------------

    def start(self) -> None:
        """
        Connect websocket and synchronize subscriptions.
        """

        self._websocket_client.connect()
        self.sync_subscriptions()

    def stop(self) -> None:
        """
        Disconnect websocket.
        """

        self._websocket_client.disconnect()
        self._active_symbols.clear()

    # ---------------------------------------------------------
    # Subscription management
    # ---------------------------------------------------------

    def sync_subscriptions(self) -> None:
        """
        Synchronize websocket subscriptions with SubscriptionRegistry.
        """

        required_symbols = self._subscription_registry.get_all_symbols()

        symbols_to_subscribe = (
            required_symbols - self._active_symbols
        )

        symbols_to_unsubscribe = (
            self._active_symbols - required_symbols
        )

        if symbols_to_subscribe:
            self._websocket_client.subscribe(
                symbols_to_subscribe
            )

        if symbols_to_unsubscribe:
            self._websocket_client.unsubscribe(
                symbols_to_unsubscribe
            )

        self._active_symbols = set(required_symbols)

    # ---------------------------------------------------------
    # Tick handling
    # ---------------------------------------------------------

    def on_tick(self, tick: Tick) -> None:
        """
        Publish incoming tick to EventBus.
        """

        event = Event(
            event_type=EventType.TICK_RECEIVED,
            payload=tick
        )

        self._event_bus.publish(event)

    # ---------------------------------------------------------
    # Testing helpers
    # ---------------------------------------------------------

    @property
    def active_symbols(self) -> set[str]:
        return set(self._active_symbols)