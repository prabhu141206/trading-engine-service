from event_system.event import Event
from event_system.event_bus import EventBus
from event_system.event_type import EventType

from candle.candle_models import CandleBatch
from indicators.indicator_models import IndicatorBatch
from strategy.strategy_factory import StrategyFactory
from registry.strategy_registry import StrategyRegistry

from .strategy_correlator import StrategyCorrelator
from .strategy_dispatcher import StrategyDispatcher
from .strategy_output import StrategyOutput

class StrategyEngine:
    """
    Orchestrates market-data flow into strategy instances.

    Responsibilities:
        - Subscribe to relevant EventBus events.
        - Correlate candle and indicator data.
        - Forward completed StrategyContext objects to the dispatcher.
        - Forward tick data to the dispatcher.

    This class does not:
        - contain strategy business logic
        - create strategy objects
        - manage users
        - perform risk checks
        - execute orders
    """

    def __init__(
        self,
        event_bus: EventBus,
        correlator: StrategyCorrelator,
        dispatcher: StrategyDispatcher,
        strategy_registry: StrategyRegistry,
        strategy_factory: StrategyFactory,
    ) -> None:
        self._event_bus = event_bus
        self._correlator = correlator
        self._dispatcher = dispatcher
        self._strategy_registry = strategy_registry
        self._strategy_factory = strategy_factory

    # ---------------------------------------------------------
    # Lifecycle
    # ---------------------------------------------------------

    def start(self) -> None:
        """
        Subscribe the strategy engine to market-data events.
        """

        self._event_bus.subscribe(
            EventType.SESSIONS_READY,
            self._on_sessions_ready,
        )
        self._event_bus.subscribe(
            EventType.CANDLE_BATCH_CLOSED,
            self._on_candle_batch,
        )

        self._event_bus.subscribe(
            EventType.INDICATOR_BATCH_UPDATED,
            self._on_indicator_batch,
        )

        self._event_bus.subscribe(
            EventType.TICK_RECEIVED,
            self._on_tick,
        )

    # ---------------------------------------------------------
    # Candle
    # ---------------------------------------------------------

    def _on_candle_batch(
        self,
        event: Event,
    ) -> None:
        """
        Process a completed candle batch.

        The correlator determines whether the corresponding
        indicator data is already available.
        """
        batch: CandleBatch = event.payload

        contexts = (
            self._correlator
            .process_candle_batch(batch)
        )

        self._dispatch_contexts(contexts)

    # ---------------------------------------------------------
    # Indicator
    # ---------------------------------------------------------

    def _on_indicator_batch(
        self,
        event: Event,
    ) -> None:
        """
        Process an updated indicator batch.

        The correlator determines whether the corresponding
        candle data is already available.
        """
        batch: IndicatorBatch = event.payload

        contexts = (
            self._correlator
            .process_indicator_batch(batch)
        )

        self._dispatch_contexts(contexts)

    # ---------------------------------------------------------
    # Tick
    # ---------------------------------------------------------

    def _on_tick(
        self,
        event: Event,
    ) -> None:
        """
        Forward tick data to eligible strategies and publish
        any strategy outputs they generate.
        """

        print(f"StrategyEngine received tick: {event.payload}")

        print(
            "StrategyEngine dispatcher class:",
            type(self._dispatcher),
            "module:",
            type(self._dispatcher).__module__,
        )

        outputs = self._dispatcher.dispatch_tick(
            event.payload
        )

        self._publish_outputs(outputs)

    # ---------------------------------------------------------
    # Context Dispatch
    # ---------------------------------------------------------

    def _dispatch_contexts(
        self,
        contexts,
    ) -> None:
        """
        Forward completed contexts to eligible strategies and publish
        any strategy outputs they generate.
        """
        for context in contexts:
            outputs = self._dispatcher.dispatch_context(
                context
            )

            self._publish_outputs(outputs)


    def _publish_outputs(
        self,
        outputs: list[StrategyOutput],
    ) -> None:
        """
        Publish strategy outputs to the EventBus.

        The StrategyEngine does not interpret the strategy output.
        It simply converts each output into a strategy event.
        """
        for output in outputs:
            self._event_bus.publish(
                Event(
                    event_type=EventType.STRATEGY_SIGNAL_GENERATED,
                    payload=output,
                )
            )



    def _on_sessions_ready(
        self,
        event: Event,
    ) -> None:
        """
        Create strategy instances from the registered strategy groups
        and provide them to the dispatcher.
        """

        groups = self._strategy_registry.get_groups()

        strategies = [
            self._strategy_factory.create(group)
            for group in groups
        ]

        self._dispatcher.set_strategies(strategies)

        print(
            f"StrategyEngine: registered {len(strategies)} strategies"
        )