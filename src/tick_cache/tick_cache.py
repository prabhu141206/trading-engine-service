from threading import Lock

from event_system.event import Event
from event_system.event_bus import EventBus
from event_system.event_type import EventType
from market_data.models import Tick


class TickCache:
    """
    Stores the latest tick per symbol.

    Responsibilities:
        - Subscribe to TICK_RECEIVED events.
        - Keep only the most recent tick for each symbol.
        - Provide O(1) latest tick lookup.
    """

    def __init__(self, event_bus: EventBus) -> None:

        self._event_bus = event_bus
        self._latest_ticks: dict[str, Tick] = {}

        # Protects concurrent reads/writes.
        self._lock = Lock()

    # ---------------------------------------------------------
    # Public API
    # ---------------------------------------------------------

    def start(self) -> None:
        """
        Register tick event subscriber.
        """

        self._event_bus.subscribe(
            EventType.TICK_RECEIVED,
            self._on_tick
        )

    def get_latest(self, symbol: str) -> Tick | None:
        """
        Return the latest tick for the symbol.
        """

        with self._lock:
            return self._latest_ticks.get(symbol)

    def has_symbol(self, symbol: str) -> bool:
        """
        Return True if a tick exists for the symbol.
        """

        with self._lock:
            return symbol in self._latest_ticks

    def clear(self) -> None:
        """
        Clear all cached ticks.
        """

        with self._lock:
            self._latest_ticks.clear()

    # ---------------------------------------------------------
    # Event Handler
    # ---------------------------------------------------------

    def _on_tick(self, event: Event) -> None:
        """
        Update latest tick for the symbol.
        """

        tick: Tick = event.payload

        with self._lock:
            self._latest_ticks[tick.symbol] = tick