from strategy.strategy_output import StrategyOutput

from .signal_delivery import SignalDelivery


class LogSignalDelivery(SignalDelivery):
    """
    Temporary delivery implementation that logs signals.

    This allows the signal-distribution pipeline to run before
    the real client delivery mechanism is implemented.
    """

    def deliver(
        self,
        user_id: int,
        signal: StrategyOutput,
    ) -> None:
        print(
            f"Signal delivered to user {user_id}: {signal}"
        )