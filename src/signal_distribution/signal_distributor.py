from registry.strategy_user_registry import StrategyUserRegistry
from strategy.strategy_output import StrategyOutput

from .signal_delivery import SignalDelivery


class SignalDistributor:
    """
    Distributes generated strategy signals to subscribed users.

    Responsibilities:
        - Receive a generated StrategyOutput.
        - Find users subscribed to its StrategyGroup.
        - Deliver the signal to each subscribed user.

    This class does not:
        - generate strategy signals
        - create strategies
        - perform risk checks
        - execute orders
        - know about WebSockets
        - know how a signal is delivered
    """

    def __init__(
        self,
        subscription_registry: StrategyUserRegistry,
        delivery: SignalDelivery,
    ) -> None:
        self._subscription_registry = subscription_registry
        self._delivery = delivery

    def distribute(
        self,
        signal: StrategyOutput,
    ) -> None:
        """
        Deliver a generated strategy signal to every subscribed user.
        """

        users = (
            self._subscription_registry.get_subscribers(
                signal.strategy_group
            )
        )

        for user_id in users:
            self._delivery.deliver(
                user_id=user_id,
                signal=signal,
            )