class FakeActiveSymbolProvider:
    """
    Provides a fixed set of active symbols for
    local development and testing.

    This will later be replaced by an implementation
    backed by SubscriptionRegistry.
    """

    def __init__(
        self,
        symbols: list[str],
    ) -> None:
        self._symbols = symbols

    def get_active_symbols(self) -> list[str]:
        """
        Return the currently active symbols.
        """
        return list(self._symbols)