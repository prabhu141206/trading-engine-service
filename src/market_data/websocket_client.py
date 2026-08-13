from typing import Callable, Iterable, Protocol

from market_data.models import Tick


class WebSocketClient(Protocol):
    """
    Broker websocket client interface.
    """

    def connect(self) -> None:
        ...

    def disconnect(self) -> None:
        ...

    def subscribe(self, symbols: Iterable[str]) -> None:
        ...

    def unsubscribe(self, symbols: Iterable[str]) -> None:
        ...

    def set_tick_handler(
        self,
        handler: Callable[[Tick], None]
    ) -> None:
        ...