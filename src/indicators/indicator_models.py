from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class SymbolIndicatorState:
    """
    Latest calculated indicator values for one symbol and timeframe.
    """

    symbol: str
    timeframe: str
    ema_10: float
    ready: bool = True


@dataclass(frozen=True)
class IndicatorBatch:
    """
    Indicator values calculated for one completed candle interval.
    """

    timeframe: str
    start_time: datetime
    end_time: datetime
    indicators: dict[str, SymbolIndicatorState]