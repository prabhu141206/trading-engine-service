class SubscriptionRegistry:
    """
    Stores the unique symbols currently required by the trading engine.

    Responsibilities:
        - Register a symbol.
        - Remove a symbol.
        - Return all registered symbols.

    This class does not:
        - Connect to a websocket.
        - Subscribe to a broker.
        - Publish events.
        - Know about users or strategies.
    """

    def __init__(self) -> None:
        self._symbols: set[str] = set()

    def add_symbol(self, symbol: str) -> None:
        """Register a symbol for market-data subscription."""
        self._symbols.add(symbol)

    def remove_symbol(self, symbol: str) -> None:
        """Remove a symbol from the registry."""
        self._symbols.discard(symbol)

    def get_symbols(self) -> set[str]:
        """Return a copy of all currently registered symbols."""
        return self._symbols.copy()

    def clear(self) -> None:
        """Remove all registered symbols."""
        self._symbols.clear()