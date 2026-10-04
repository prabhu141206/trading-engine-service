from datetime import datetime
from unittest.mock import Mock

from market_data.models import Tick

from event_system.event import Event
from event_system.event_type import EventType

from registry.strategy_registry import StrategyRegistry

from strategy.strategy_context import StrategyContext
from strategy.strategy_dispatcher import StrategyDispatcher
from strategy.strategy_engine import StrategyEngine
from strategy.strategy_factory import StrategyFactory
from strategy.strategy_models import StrategyGroup
from strategy.strategy_output import (
    SignalSide,
    SignalType,
    StrategyOutput,
)
from strategy.strategy_requirements import StrategyRequirements
from strategy.strategy_state import StrategyState


class FakeSignalStrategy:
    """
    Minimal strategy used to verify StrategyOutput propagation.

    The strategy always generates a predefined signal when it receives
    a context or tick.
    """

    def __init__(
        self,
        symbol: str = "NIFTY",
    ) -> None:
        self.symbol = symbol
        self.timeframe = "5m"
        self.state = StrategyState.IDLE

        # This uniquely identifies the computation performed by
        # this strategy instance.
        self.strategy_group = StrategyGroup(
            strategy_type="EMA",
            symbol=self.symbol,
            timeframe=self.timeframe,
            parameters=(("period", 10),),
        )

        self.received_contexts = []
        self.received_ticks = []

    def get_requirements(self) -> StrategyRequirements:
        """
        Declare that this strategy requires 5m contexts and ticks.
        """
        return StrategyRequirements(
            candle_timeframes=("5m",),
            indicators=("EMA_10",),
            requires_ticks=True,
        )

    def on_context(
        self,
        context: StrategyContext,
    ) -> StrategyOutput:
        """
        Generate a deterministic entry signal for testing.
        """
        self.received_contexts.append(context)

        return StrategyOutput(
            strategy_group=self.strategy_group,
            signal_type=SignalType.ENTRY,
            side=SignalSide.BUY,
            timestamp=context.end_time,
        )

    def on_tick(
        self,
        context: StrategyContext,
    ) -> StrategyOutput:
        """
        Generate a deterministic tick-based signal for testing.
        """
        self.received_ticks.append(context)

        return StrategyOutput(
            strategy_group=self.strategy_group,
            signal_type=SignalType.ENTRY,
            side=SignalSide.BUY,
            timestamp=context.end_time,
        )


def create_context() -> StrategyContext:
    """
    Create a completed strategy context for testing.
    """
    return StrategyContext(
        symbol="NIFTY",
        timeframe="5m",
        start_time=datetime(2026, 8, 24, 10, 15),
        end_time=datetime(2026, 8, 24, 10, 20),
    )


def create_engine(
    strategy: FakeSignalStrategy,
):
    """
    Build the real Dispatcher and Engine while mocking only the
    EventBus and Correlator.

    This isolates the signal propagation path being tested.
    """

    # Mock the external event system because these tests
    # focus on StrategyOutput propagation.
    event_bus = Mock()

    # Mock the correlator because completed contexts are
    # supplied directly by the test.
    correlator = Mock()

    # Create the real dispatcher with the test strategy.
    dispatcher = StrategyDispatcher(
        strategies=[strategy],
    )

    # StrategyEngine now requires a registry and factory.
    # They are not the focus of these tests, but valid
    # dependencies are required by the current constructor.
    strategy_registry = StrategyRegistry()
    strategy_factory = StrategyFactory()

    engine = StrategyEngine(
        event_bus=event_bus,
        correlator=correlator,
        dispatcher=dispatcher,
        strategy_registry=strategy_registry,
        strategy_factory=strategy_factory,
    )

    return engine, event_bus, correlator


def test_tick_strategy_output_is_published():
    """
    Verify the complete tick-based signal path.

    A tick is routed to a strategy requiring ticks, the strategy
    generates an output, and StrategyEngine publishes the output.
    """

    strategy = FakeSignalStrategy()

    engine, event_bus, _ = create_engine(
        strategy
    )

    tick = Tick(
        symbol="NIFTY",
        price=25100.5,
        timestamp=datetime(2026, 8, 24, 10, 20),
    )

    tick_event = Event(
        event_type=EventType.TICK_RECEIVED,
        payload=tick,
    )

    engine._on_tick(tick_event)

    # The strategy must receive exactly one tick context.
    assert len(strategy.received_ticks) == 1

    received_context = strategy.received_ticks[0]

    # The original Tick object must be preserved.
    assert received_context.tick is tick

    # The context must contain the correct routing information.
    assert received_context.symbol == "NIFTY"
    assert received_context.timeframe == "5m"

    # Exactly one strategy signal should be published.
    event_bus.publish.assert_called_once()

    published_event = (
        event_bus.publish.call_args.args[0]
    )

    # The correct event type must be published.
    assert (
        published_event.event_type
        is EventType.STRATEGY_SIGNAL_GENERATED
    )

    # The exact StrategyGroup must be preserved.
    assert (
        published_event.payload.strategy_group
        == strategy.strategy_group
    )

    # The signal must belong to NIFTY.
    assert (
        published_event.payload.strategy_group.symbol
        == "NIFTY"
    )

def test_no_strategy_output_means_no_event_published():
    """
    Verify that when a strategy produces no signal, the StrategyEngine
    does not publish a strategy event.
    """

    strategy = Mock()

    strategy.symbol = "NIFTY"
    strategy.timeframe = "5m"

    strategy.get_requirements.return_value = (
        StrategyRequirements(
            candle_timeframes=("5m",),
            indicators=("EMA_10",),
            requires_ticks=True,
        )
    )

    strategy.on_context.return_value = None

    engine, event_bus, correlator = create_engine(
        strategy
    )

    context = create_context()

    correlator.process_candle_batch.return_value = [
        context
    ]

    batch_event = Mock()
    batch_event.payload = Mock()

    engine._on_candle_batch(batch_event)

    # The strategy must receive the context.
    strategy.on_context.assert_called_once_with(
        context
    )

    # No signal means no event should be published.
    event_bus.publish.assert_not_called()


def test_multiple_strategy_outputs_are_published():
    """
    Verify that multiple strategies can generate signals from the
    same market context and every signal is published independently.
    """

    first_strategy = FakeSignalStrategy(
        symbol="NIFTY"
    )

    second_strategy = FakeSignalStrategy(
        symbol="NIFTY"
    )

    event_bus = Mock()
    correlator = Mock()

    dispatcher = StrategyDispatcher(
        strategies=[
            first_strategy,
            second_strategy,
        ]
    )

    # Current StrategyEngine constructor requires
    # registry and factory dependencies.
    strategy_registry = StrategyRegistry()
    strategy_factory = StrategyFactory()

    engine = StrategyEngine(
        event_bus=event_bus,
        correlator=correlator,
        dispatcher=dispatcher,
        strategy_registry=strategy_registry,
        strategy_factory=strategy_factory,
    )

    context = create_context()

    correlator.process_candle_batch.return_value = [
        context
    ]

    batch_event = Mock()
    batch_event.payload = Mock()

    engine._on_candle_batch(batch_event)

    # Both strategies generated a signal.
    assert event_bus.publish.call_count == 2

    for call in event_bus.publish.call_args_list:

        published_event = call.args[0]

        # Every output must become a strategy signal event.
        assert (
            published_event.event_type
            is EventType.STRATEGY_SIGNAL_GENERATED
        )

        # Every signal must carry its StrategyGroup identity.
        assert (
            published_event.payload.strategy_group
            is not None
        )

        # Both strategies are configured for NIFTY.
        assert (
            published_event.payload.strategy_group.symbol
            == "NIFTY"
        )