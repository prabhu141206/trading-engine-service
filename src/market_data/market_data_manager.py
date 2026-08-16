from event_system.event import Event
from event_system.event_bus import EventBus
from event_system.event_type import EventType

from market_data.models import Tick
from market_data.websocket_client import WebSocketClient
from registry.subscription_registry import SubscriptionRegistry

class MarketDataManager:
    """
    Manages broker websocket connection and publishes live ticks.

    Responsibilities:
        - Connect/disconnect websocket.
        - Subscribe required symbols.
        - Publish TICK_RECEIVED events.
    """

    def __init__(
        self,
        event_bus: EventBus,
        subscription_registry: SubscriptionRegistry,
        websocket_client: WebSocketClient
    ) -> None:


        # ---------------------------------------------------------
        # Dependencies 
        # ---------------------------------------------------------
        self._event_bus = event_bus
        self._subscription_registry = subscription_registry
        self._websocket_client = websocket_client

        # ---------------------------------------------------------
        # Internal State
        # ---------------------------------------------------------
        self._connected = False
        self._subscribed_symbols: set[str] = set()

    # ---------------------------------------------------------
    # Public API
    # ---------------------------------------------------------

    def start(self) -> None:
        """
        Register lifecycle event handlers.
        """

        self._event_bus.subscribe(
            EventType.SESSIONS_READY,
            self._on_sessions_ready
        )

        self._event_bus.subscribe(
            EventType.MARKET_CLOSE,
            self._on_market_close
        )

    # ---------------------------------------------------------
    # Event Handlers
    # ---------------------------------------------------------

    def _on_sessions_ready(self, event: Event) -> None:
        """
        Called after SessionManager has populated SubscriptionRegistry.
        """

        self._connect()
        self._sync_subscriptions()

    def _on_market_close(self, event: Event) -> None:
        """
        Disconnect websocket and clear runtime subscription state.
        """

        if not self._connected:
            return

        if self._subscribed_symbols:
            self._websocket_client.unsubscribe(
                self._subscribed_symbols
            )

        self._websocket_client.disconnect()

        self._connected = False
        self._subscribed_symbols.clear()

    # ---------------------------------------------------------
    # Connection Management
    # ---------------------------------------------------------

    def _connect(self) -> None:
        """
        Establish websocket connection if not already connected.
        """

        if self._connected:
            return

        self._websocket_client.set_tick_handler(self._on_tick)
        self._websocket_client.connect()

        self._connected = True

    def _sync_subscriptions(self) -> None:
        """
        Synchronize broker subscriptions with SubscriptionRegistry.
        """

        required_symbols = (
            self._subscription_registry.get_symbols()
        )

        to_add = required_symbols - self._subscribed_symbols

        if to_add:
            self._websocket_client.subscribe(to_add)

        self._subscribed_symbols.update(to_add)

    # ---------------------------------------------------------
    # Tick Processing
    # ---------------------------------------------------------

    def _on_tick(self, tick: Tick) -> None:
        """
        Publish incoming tick to EventBus.
        """

        self._event_bus.publish(
            Event(
                event_type=EventType.TICK_RECEIVED,
                payload=tick
            )
        )