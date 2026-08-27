from strategy.strategy_models import StrategyGroup
from registry.strategy_registry import StrategyRegistry


def create_group(
    strategy_type="EMA",
    symbol="NIFTY",
    timeframe="5m",
    period=10,
):
    """
    Create a reusable StrategyGroup for registry tests.

    Keeping test object creation in one helper avoids repeating the
    same configuration throughout the test cases.
    """
    return StrategyGroup(
        strategy_type=strategy_type,
        symbol=symbol,
        timeframe=timeframe,
        parameters=(("period", period),),
    )


def test_register_strategy_group():
    """
    Verify that a StrategyGroup can be registered successfully.
    """
    registry = StrategyRegistry()
    group = create_group()

    registry.add_group(group)

    assert group in registry.get_groups()


def test_duplicate_groups_are_registered_only_once():
    """
    Verify that identical StrategyGroups are deduplicated.

    Multiple users may subscribe to the same strategy + symbol +
    timeframe + parameters combination, but the registry should keep
    only one unique group.
    """
    registry = StrategyRegistry()

    first = create_group()
    second = create_group()

    registry.add_group(first)
    registry.add_group(second)

    assert len(registry.get_groups()) == 1


def test_different_groups_are_registered_separately():
    """
    Verify that different strategy groups are stored independently.

    EMA + NIFTY and EMA + RELIANCE represent two different strategy
    computation groups.
    """
    registry = StrategyRegistry()

    ema_nifty = create_group(symbol="NIFTY")
    ema_reliance = create_group(symbol="RELIANCE")

    registry.add_group(ema_nifty)
    registry.add_group(ema_reliance)

    assert len(registry.get_groups()) == 2


def test_remove_strategy_group():
    """
    Verify that a registered StrategyGroup can be removed.
    """
    registry = StrategyRegistry()
    group = create_group()

    registry.add_group(group)
    registry.remove_group(group)

    assert group not in registry.get_groups()


def test_clear_registry():
    """
    Verify that clear() removes every registered StrategyGroup.

    This is useful when rebuilding the registry during lifecycle
    operations such as startup or configuration refresh.
    """
    registry = StrategyRegistry()

    registry.add_group(create_group(symbol="NIFTY"))
    registry.add_group(create_group(symbol="RELIANCE"))

    registry.clear()

    assert registry.get_groups() == set()