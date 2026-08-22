from candle.candle_models import Candle


class FakeHistoricalCandleProvider:
    """
    Fake historical data provider used for tests
    and local development.
    """

    def __init__(
        self,
        candles_by_symbol: dict[str, list[Candle]],
    ) -> None:

        self._candles_by_symbol = (
            candles_by_symbol
        )

    def get_historical_candles(
        self,
        symbol: str,
        timeframe: str,
        limit: int,
    ) -> list[Candle]:

        candles = self._candles_by_symbol.get(
            symbol,
            [],
        )

        return candles[-limit:]