from collections.abc import Callable

from market_data.tick import Tick


class FakeWebSocketClient:
    """
    Fake websocket client used for local development and tests.
    """

    def __init__(self) -> None:

        self.connected = False
        self.subscribed_symbols: set[str] = set()
        self._tick_handler: Callable[[Tick], None] | None = None

    def connect(self) -> None:

        self.connected = True

    def disconnect(self) -> None:

        self.connected = False

    def subscribe(self, symbols: set[str]) -> None:

        self.subscribed_symbols.update(symbols)

    def unsubscribe(self, symbols: set[str]) -> None:

        self.subscribed_symbols.difference_update(symbols)

    def set_tick_handler(
        self,
        handler: Callable[[Tick], None]
    ) -> None:

        self._tick_handler = handler

    def emit_tick(self, tick: Tick) -> None:
        """
        Simulate an incoming websocket tick.
        """

        if self._tick_handler is not None:
            self._tick_handler(tick)