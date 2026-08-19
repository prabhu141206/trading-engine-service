from typing import Callable, Iterable

from market_data.models import Tick


class FakeWebSocketClient:
    """
    In-memory WebSocket implementation used for
    engine simulation and integration testing.

    It does not connect to a real broker.
    """

    def __init__(self) -> None:
        self.connected = False
        self.subscribed: set[str] = set()
        self._tick_handler: Callable[[Tick], None] | None = None

    def connect(self) -> None:
        self.connected = True

    def disconnect(self) -> None:
        self.connected = False

    def subscribe(
        self,
        symbols: Iterable[str],
    ) -> None:
        self.subscribed.update(symbols)

    def unsubscribe(
        self,
        symbols: Iterable[str],
    ) -> None:
        self.subscribed.difference_update(symbols)

    def set_tick_handler(
        self,
        handler: Callable[[Tick], None],
    ) -> None:
        self._tick_handler = handler

    def emit_tick(
        self,
        tick: Tick,
    ) -> None:
        """
        Simulate a broker sending a market tick.
        """

        if self._tick_handler is not None:
            self._tick_handler(tick)