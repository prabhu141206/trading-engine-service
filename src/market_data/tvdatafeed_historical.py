from datetime import timedelta

from tvDatafeed import TvDatafeed, Interval

from candle.candle_models import Candle
from market_data.historical_data_provider import HistoricalCandleProvider

class TvDatafeedHistoricalProvider(HistoricalCandleProvider):
    def __init__(self, tv_datafeed: TvDatafeed) -> None:
        self._tv_datafeed = tv_datafeed

    def get_historical_candles(
        self,
        symbol: str,
        timeframe: str,
        limit: int,
    ) -> list[Candle]:

        interval = self._get_interval(timeframe)

        provider_symbol = symbol

        if symbol == "FINNIFTY":
            provider_symbol = "NIFTY_FIN_SERVICE"

        data = self._tv_datafeed.get_hist(
            symbol=provider_symbol,
            exchange="NSE",
            interval=interval,
            n_bars=limit,
        )

        if data is None or data.empty:
            raise RuntimeError(
                f"No historical data returned for {symbol}."
            )

        candles = []

        for timestamp, row in data.iterrows():
            candle = Candle(
                symbol=symbol,
                timeframe=timeframe,
                start_time=timestamp,
                end_time=timestamp + timedelta(minutes=5),
                open=float(row["open"]),
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
            )
            candles.append(candle)

        return candles

    @staticmethod
    def _get_interval(timeframe: str) -> Interval:
        if timeframe in {"5m", "5minute"}:
            return Interval.in_5_minute

        raise ValueError(
            f"Unsupported timeframe for tvDatafeed: {timeframe}"
        )