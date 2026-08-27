from datetime import datetime

from strategy.strategy_dispatcher import StrategyDispatcher
from strategy.strategy_factory import StrategyFactory
from strategy.strategy_models import (
    StrategyGroup,
    StrategyType,
)
from registry.strategy_registry import StrategyRegistry
from strategy.strategy_state import StrategyState


def create_ema_group(
    symbol: str = "NIFTY",
) -> StrategyGroup:
    """
    Create the unique EMA + symbol computation group used by
    the integration test.
    """
    return StrategyGroup(
        strategy_type=StrategyType.EMA,
        symbol=symbol,
        timeframe="5m",
        parameters=(("period", 10),),
    )


def test_registry_factory_dispatcher_integration():
    """
    Verify the complete strategy construction and routing pipeline.

    The registry stores the unique StrategyGroup.
    The factory creates the corresponding strategy object.
    The dispatcher indexes the created object.
    The strategy then receives matching market context.
    """

    # ---------------------------------------------------------
    # 1. Register the unique strategy computation group.
    # ---------------------------------------------------------

    registry = StrategyRegistry()

    group = create_ema_group()

    registry.add_group(group)

    assert group in registry.get_groups()

    # ---------------------------------------------------------
    # 2. Create concrete strategy objects from the registry.
    # ---------------------------------------------------------

    factory = StrategyFactory()

    strategies = [
        factory.create(group)
        for group in registry.get_groups()
    ]

    assert len(strategies) == 1

    strategy = strategies[0]

    assert strategy.symbol == "NIFTY"
    assert strategy.timeframe == "5m"

    # A newly created strategy must start from IDLE.
    assert strategy.state is StrategyState.IDLE

    # ---------------------------------------------------------
    # 3. Build the dispatcher from the created objects.
    # ---------------------------------------------------------

    dispatcher = StrategyDispatcher(
        strategies=strategies,
    )

    # ---------------------------------------------------------
    # 4. Create matching market context.
    # ---------------------------------------------------------

    context = create_context()

    # ---------------------------------------------------------
    # 5. Dispatch the context.
    # ---------------------------------------------------------

    outputs = dispatcher.dispatch_context(
        context
    )

    # ---------------------------------------------------------
    # 6. Verify that the correct strategy received it.
    # ---------------------------------------------------------

    # The current EMAStrategy is only a skeleton, so it does not
    # generate a signal yet.
    assert outputs == []


def test_registry_creates_independent_computation_groups():
    """
    Verify that different strategy + symbol combinations remain
    independent computation groups.

    EMA + NIFTY and EMA + RELIANCE must produce two strategy objects.
    """

    registry = StrategyRegistry()

    nifty_group = create_ema_group(
        symbol="NIFTY"
    )

    reliance_group = create_ema_group(
        symbol="RELIANCE"
    )

    registry.add_group(nifty_group)
    registry.add_group(reliance_group)

    factory = StrategyFactory()

    strategies = [
        factory.create(group)
        for group in registry.get_groups()
    ]

    assert len(strategies) == 2

    symbols = {
        strategy.symbol
        for strategy in strategies
    }

    assert symbols == {
        "NIFTY",
        "RELIANCE",
    }


def test_duplicate_strategy_group_creates_only_one_strategy():
    """
    Verify the key property of StrategyGroup.

    If multiple users select the exact same strategy + symbol +
    timeframe + parameters combination, the registry stores only
    one computation group.

    Therefore only one strategy object is created.
    """

    registry = StrategyRegistry()

    group_one = create_ema_group("NIFTY")
    group_two = create_ema_group("NIFTY")

    registry.add_group(group_one)
    registry.add_group(group_two)

    assert len(registry.get_groups()) == 1

    factory = StrategyFactory()

    strategies = [
        factory.create(group)
        for group in registry.get_groups()
    ]

    assert len(strategies) == 1


def create_context():
    """
    Create a matching NIFTY 5-minute strategy context.
    """
    from strategy.strategy_context import StrategyContext

    start_time = datetime(
        2026,
        8,
        24,
        10,
        15,
    )

    end_time = datetime(
        2026,
        8,
        24,
        10,
        20,
    )

    return StrategyContext(
        symbol="NIFTY",
        timeframe="5m",
        start_time=start_time,
        end_time=end_time,
    )