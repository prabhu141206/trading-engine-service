from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class StrategyRequirements:
    """
    Declares the market-data requirements of a strategy.

    The requirements belong to the strategy type, not to a
    particular user or symbol.

    Example:

        EMA strategy:
            candle_timeframes = ("5m",)
            indicators = ("EMA_10",)
            requires_ticks = True

        VWAP strategy:
            candle_timeframes = ("15m",)
            indicators = ("VWAP",)
            requires_ticks = False
    """

    candle_timeframes: Tuple[str, ...] = ()
    indicators: Tuple[str, ...] = ()
    requires_ticks: bool = False