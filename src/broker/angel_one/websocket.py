from typing import Callable, Iterable
from datetime import datetime
import threading

from SmartApi.smartWebSocketV2 import SmartWebSocketV2

from broker.angel_one.authentication import (
    AngelOneAuthenticator,
)
from broker.angel_one.instrument_master import (
    AngelOneInstrumentMaster,
)
from market_data.models import Tick
from market_data.websocket_client import WebSocketClient


class AngelOneWebSocket:
    """
    Angel One implementation of the application's
    generic WebSocketClient interface.
    """

    def __init__(
        self,
        authenticator: AngelOneAuthenticator,
        instrument_master: AngelOneInstrumentMaster,
    ) -> None:
        self._authenticator = authenticator
        self._instrument_master = instrument_master

        self._websocket: SmartWebSocketV2 | None = None
        self._tick_handler: Callable[[Tick], None] | None = None

        self._pending_symbols: set[str] = set()

        self._socket_open = False

    def connect(self) -> None:
        """
        Authenticate and establish the Angel One
        WebSocket V2 connection.
        """

        session = self._authenticator.login()

        self._websocket = SmartWebSocketV2(
            auth_token=session.auth_token,
            api_key=self._authenticator.get_api_key(),
            client_code=self._authenticator.get_client_code(),
            feed_token=session.feed_token,
        )

        self._websocket.on_open = self._on_open
        self._websocket.on_data = self._on_data
        self._websocket.on_error = self._on_error
        self._websocket.on_close = self._on_close

        thread = threading.Thread(
            target=self._websocket.connect,
            daemon=True,
        )
        
        thread.start()

    def disconnect(self) -> None:
        if self._websocket is None:
            return

        self._websocket.close_connection()
        self._websocket = None

    def subscribe(self, symbols: Iterable[str]) -> None:
        if self._websocket is None:
            raise RuntimeError("WebSocket is not connected.")

        self._pending_symbols.update(symbols)

        print(f"subscribe() called. socket_open={self._socket_open}, pending={self._pending_symbols}")

        if not self._socket_open:
            return

        self._subscribe_pending_symbols()

    def unsubscribe(
        self,
        symbols: Iterable[str],
    ) -> None:
        if self._websocket is None:
            return

        tokens = self._instrument_master.get_tokens(
            set(symbols)
        )

        token_list = [
            {
                "exchangeType": 1,
                "tokens": list(tokens.values()),
            }
        ]

        self._websocket.unsubscribe(
            "market-data",
            1,
            token_list,
        )

    def set_tick_handler(
        self,
        handler: Callable[[Tick], None],
    ) -> None:
        self._tick_handler = handler

    def _on_open(self, wsapp) -> None:
        print("Angel One WebSocket connected")

        self._socket_open = True

        print(f"Pending symbols to subscribe: {self._pending_symbols}")

        self._subscribe_pending_symbols()

    def _subscribe_pending_symbols(self) -> None:
        if not self._pending_symbols:
            return

        tokens = self._instrument_master.get_tokens(self._pending_symbols)

        token_list = [
            {
                "exchangeType": 1,
                "tokens": list(tokens.values()),
            }
        ]

        print(f"Subscribing to symbols: {self._pending_symbols}")

        self._websocket.subscribe(
            correlation_id="market-data",
            mode=1,
            token_list=token_list,
        )

        self._pending_symbols.clear()
    def _on_data(self, wsapp, message) -> None:

        print(
            f"Angel One raw tick: "
            f"exchange_timestamp={message.get('exchange_timestamp')}, "
            f"last_traded_price={message.get('last_traded_price')}, "
            f"token={message.get('token')}"
        )
        token = message["token"]

        symbol = self._instrument_master.get_symbol(token)

        price = message["last_traded_price"] / 100

        timestamp = datetime.fromtimestamp(
            message["exchange_timestamp"] / 1000
        )

        tick = Tick(
            symbol=symbol,
            price=price,
            timestamp=timestamp,
        )

        print(f"Angel One tick converted: {tick}")

        if self._tick_handler is not None:
            self._tick_handler(tick)


    def _on_error(self, wsapp, error) -> None:
        print(f"Angel One WebSocket error: {error}")


    def _on_close(self, wsapp) -> None:
        print("Angel One WebSocket closed")