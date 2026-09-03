from abc import ABC, abstractmethod

from strategy.strategy_output import StrategyOutput


class SignalDelivery(ABC):
    """
    Defines how a generated strategy signal is delivered to a user.

    The SignalDistributor depends on this abstraction rather than
    knowing how the signal actually reaches the user.
    """

    @abstractmethod
    def deliver(
        self,
        user_id: int,
        signal: StrategyOutput,
    ) -> None:
        """
        Deliver a strategy signal to one user.
        """
        raise NotImplementedError