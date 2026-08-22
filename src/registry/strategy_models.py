from dataclasses import dataclass


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