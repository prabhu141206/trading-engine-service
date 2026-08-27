from typing import Protocol

from .strategy_context import StrategyContext
from .strategy_output import StrategyOutput
from .strategy_requirements import StrategyRequirements


class Strategy(Protocol):
    """
    Contract that every strategy implementation must follow.
    """

    @property
    def symbol(self) -> str:
        """
        Symbol operated on by this strategy instance.
        """
        ...

    @property
    def timeframe(self) -> str:
        """
        Primary timeframe of this strategy instance.
        """
        ...

    def get_requirements(self) -> StrategyRequirements:
        """
        Return the data requirements of the strategy.
        """
        ...

    def on_context(
        self,
        context: StrategyContext,
    ) -> StrategyOutput | None:
        """
        Process a completed strategy context.
        """
        ...

    def on_tick(
        self,
        context: StrategyContext,
    ) -> StrategyOutput | None:
        """
        Process tick data when required.
        """
        ...