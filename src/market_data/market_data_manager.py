from event_system.event import Event
from event_system.event_bus import EventBus
from event_system.event_type import EventType

from market_data.models import Tick
from market_data.websocket_client import WebSocketClient
from monitoring.system_monitor import SystemMonitor
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
        websocket_client: WebSocketClient,
        system_monitor: SystemMonitor,
    ) -> None:


        # ---------------------------------------------------------
        # Dependencies 
        # ---------------------------------------------------------
        self._event_bus = event_bus
        self._subscription_registry = subscription_registry
        self._websocket_client = websocket_client
        self._system_monitor = system_monitor

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
        Register lifecycle event handler, also 
        establish websocket connection.
        """

        self._event_bus.subscribe(
            EventType.SESSIONS_READY,
            self._on_sessions_ready
        )

        self._event_bus.subscribe(
            EventType.MARKET_PROCESSING_COMPLETE,
            self._on_market_processing_complete,
        )

        self._event_bus.subscribe(
            EventType.MARKET_CLOSE,
            self._on_market_close,
        )

        self._websocket_client.set_tick_handler(self._on_tick)
        

    # ---------------------------------------------------------
    # Event Handlers
    # ---------------------------------------------------------

    def _on_sessions_ready(self, event: Event) -> None:
        """
        Called after SessionManager has populated SubscriptionRegistry.
        """

        print("MarketDataManager: SESSIONS_READY received")

        self._connect()

        print("MarketDataManager: connect() returned")

        self._sync_subscriptions()

        self._accepting_ticks = True

        print("MarketDataManager: subscriptions synced")

    def _on_market_processing_complete(self, event: Event) -> None:
        """
        Disconnect websocket and clear runtime subscription state
        after market processing has completed.
        """

        if not self._connected:
            return

        if self._subscribed_symbols:
            self._websocket_client.unsubscribe(
                self._subscribed_symbols
            )

        self._websocket_client.disconnect()

        self._connected = False

        self._system_monitor.update_market_state("DISCONNECTED")
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

        self._system_monitor.update_market_state("CONNECTED")

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

        self._system_monitor.update_active_symbols(
            len(self._subscribed_symbols)
        )

    # ---------------------------------------------------------
    # Tick Processing
    # ---------------------------------------------------------

    def _on_tick(self, tick: Tick) -> None:
        """
        Publish incoming ticks only while the market-data
        pipeline is accepting live ticks.
        """

        if not self._accepting_ticks:
            return

        self._system_monitor.record_tick()

        self._event_bus.publish(
            Event(
                event_type=EventType.TICK_RECEIVED,
                payload=tick,
            )
        )


    def _on_market_close(
        self,
        event: Event,
    ) -> None:
        """
        Stop accepting new market ticks when the market
        processing phase begins to close.
        """

        self._accepting_ticks = False