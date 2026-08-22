from dataclasses import dataclass
from datetime import datetime


@dataclass
class Candle:
    symbol: str
    timeframe: str
    start_time: datetime
    end_time: datetime
    open: float
    high: float
    low: float
    close: float


@dataclass
class CandleBatch:
    timeframe: str
    start_time: datetime
    end_time: datetime
    candles: dict[str, Candle]