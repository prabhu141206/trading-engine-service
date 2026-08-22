from typing import Protocol


class ActiveSymbolProvider(Protocol):
    """
    Provides the symbols that currently require
    indicator state.
    """

    def get_active_symbols(self) -> list[str]:
        """
        Return all currently active market symbols.
        """
        ...