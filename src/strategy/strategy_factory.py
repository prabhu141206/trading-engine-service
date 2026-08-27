from .strategy_interface import Strategy
from .strategy_models import StrategyGroup, StrategyType
from .strategies.ema_strategy import EMAStrategy


class StrategyFactory:
    """
    Creates concrete strategy instances from StrategyGroup configuration.

    The factory is responsible only for object creation.
    """

    def create(self, group: StrategyGroup) -> Strategy:
        """
        Create the concrete strategy represented by the group.
        """

        if group.strategy_type is StrategyType.EMA:
            return EMAStrategy(
                symbol=group.symbol,
                timeframe=group.timeframe,
                parameters=group.parameters,
            )

        raise ValueError(
            f"Unsupported strategy type: {group.strategy_type}"
        )