from dataclasses import dataclass
from enum import Enum


class StrategyType(str, Enum):
    """
    Identifies the supported strategy types.

    The enum provides a stable identifier for strategy selection
    and factory dispatch.
    """

    EMA = "EMA"
    VWAP = "VWAP"


@dataclass(frozen=True)
class StrategyGroup:
    """
    Identifies one unique strategy computation group.

    Two groups are considered identical when all their
    configuration fields are identical.
    """

    """
        StrategyGroup
        (
            strategy_type="EMA",
            symbol="NIFTY",
            timeframe="5m",
            parameters=(("period", 10),)
        )
    """

    strategy_type: str
    symbol: str
    timeframe: str
    parameters: tuple[tuple[str, object], ...] = ()