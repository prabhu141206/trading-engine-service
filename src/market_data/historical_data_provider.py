from typing import Protocol

from candle.candle_models import Candle


class HistoricalCandleProvider(Protocol):
    """
    Interface for retrieving historical candles.

    Implementations may retrieve data from:
        - Broker APIs
        - Market-data providers
        - Local databases
        - Backtesting datasets
    """

    def get_historical_candles(
        self,
        symbol: str,
        timeframe: str,
        limit: int,
    ) -> list[Candle]:
        """
        Return historical candles for a symbol.

        Args:
            symbol:
                Market symbol.

            timeframe:
                Candle timeframe, for example "5m".

            limit:
                Maximum number of candles required.

        Returns:
            List of historical Candle objects.
        """
        ...