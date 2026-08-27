from dataclasses import dataclass
from datetime import datetime
from typing import Any

from candle.candle_models import Candle


@dataclass(frozen=True)
class StrategyContext:
    """
    Prepared market-data context supplied to a strategy.

    The context represents one specific market interval.

    The Strategy Engine is responsible for constructing this context
    after the required market-data events have been correlated.
    """

    symbol: str
    timeframe: str

    start_time: datetime
    end_time: datetime

    candle: Candle | None = None
    indicators: dict[str, Any] | None = None
    tick: Any = None