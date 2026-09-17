from datetime import datetime, timedelta

from SmartApi import SmartConnect

from candle.candle_models import Candle
from broker.angel_one.instrument_master import (
    AngelOneInstrumentMaster,
)


class AngelOneHistoricalDataProvider:
    """
    Fetches historical OHLC candles from Angel One.
    """

    def __init__(
        self,
        smart_api: SmartConnect,
        instrument_master: AngelOneInstrumentMaster,
    ) -> None:
        self._smart_api = smart_api
        self._instrument_master = instrument_master

    def get_historical_candles(
        self,
        symbol: str,
        timeframe: str,
        limit: int,
    ) -> list[Candle]:

        token = self._instrument_master.get_token(symbol)

        todate = datetime.now()
        fromdate = todate - timedelta(days=5)

        historic_params = {
            "exchange": "NSE",
            "symboltoken": token,
            "interval": timeframe,
            "fromdate": fromdate.strftime("%Y-%m-%d %H:%M"),
            "todate": todate.strftime("%Y-%m-%d %H:%M"),
        }

        print(f"Historical API request: symbol={symbol}, timeframe={timeframe}, limit={limit}")
        print(f"Historical API params: {historic_params}")

        response = self._smart_api.getCandleData(
            historic_params
        )

        if not response.get("status"):
            raise RuntimeError(
                f"Failed to fetch historical data for "
                f"{symbol}: {response}"
            )

        rows = response.get("data", [])

        if len(rows) < limit:
            raise RuntimeError(
                f"Not enough historical candles for {symbol}. "
                f"Required: {limit}, received: {len(rows)}"
            )

        rows = rows[-limit:]

        candles = []

        for row in rows:
            timestamp = datetime.fromisoformat(
                row[0].replace("Z", "+00:00")
            )

            candle = Candle(
                symbol=symbol,
                timeframe=timeframe,
                start_time=timestamp,
                end_time=timestamp + timedelta(minutes=5),
                open=float(row[1]),
                high=float(row[2]),
                low=float(row[3]),
                close=float(row[4]),
            )

            candles.append(candle)

        return candles