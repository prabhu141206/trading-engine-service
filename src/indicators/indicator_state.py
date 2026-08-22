from indicators.indicator_models import SymbolIndicatorState


class IndicatorStateStore:
    """
    In-memory store for the latest indicator state of each symbol.
    """

    def __init__(self) -> None:
        self._states: dict[
            tuple[str, str],
            SymbolIndicatorState,
        ] = {}

    def set(
        self,
        state: SymbolIndicatorState,
    ) -> None:
        key = (
            state.symbol,
            state.timeframe,
        )

        self._states[key] = state

    def get(
        self,
        symbol: str,
        timeframe: str,
    ) -> SymbolIndicatorState | None:

        return self._states.get(
            (symbol, timeframe)
        )

    def remove(
        self,
        symbol: str,
        timeframe: str,
    ) -> None:

        self._states.pop(
            (symbol, timeframe),
            None,
        )

    def is_ready(
        self,
        symbol: str,
        timeframe: str,
    ) -> bool:

        state = self.get(
            symbol,
            timeframe,
        )

        return (
            state is not None
            and state.ready
        )