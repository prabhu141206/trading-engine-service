from event_system.event import Event
from event_system.event_bus import EventBus
from event_system.event_type import EventType

from registry.strategy_user_registry import StrategyUserRegistry
from strategy.strategy_output import StrategyOutput

from .signal_delivery import SignalDelivery


class SignalDistributor:
    """
    Distributes generated strategy signals to subscribed users.

    Responsibilities:
        - Subscribe to strategy signal events.
        - Receive generated StrategyOutput.
        - Find users subscribed to its StrategyGroup.
        - Deliver the signal to each subscribed user.

    This class does not:
        - generate strategy signals
        - create strategies
        - perform risk checks
        - execute orders
        - know about WebSockets
    """

    def __init__(
        self,
        event_bus: EventBus,
        subscription_registry: StrategyUserRegistry,
        delivery: SignalDelivery,
    ) -> None:
        self._event_bus = event_bus
        self._subscription_registry = subscription_registry
        self._delivery = delivery

    # ---------------------------------------------------------
    # Lifecycle
    # ---------------------------------------------------------

    def start(self) -> None:
        """
        Subscribe to generated strategy signals.
        """
        self._event_bus.subscribe(
            EventType.STRATEGY_SIGNAL_GENERATED,
            self._on_strategy_signal,
        )

    # ---------------------------------------------------------
    # Event handling
    # ---------------------------------------------------------

    def _on_strategy_signal(
        self,
        event: Event,
    ) -> None:
        """
        Receive a strategy signal from the EventBus and distribute it.
        """
        signal: StrategyOutput = event.payload

        self.distribute(signal)

    # ---------------------------------------------------------
    # Distribution
    # ---------------------------------------------------------

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