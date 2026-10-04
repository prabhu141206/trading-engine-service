from strategy.strategy_models import StrategyGroup
from registry.strategy_registry import StrategyRegistry


def test_add_strategy():
    """
    Test Case:
    Verify that a single strategy group can be added to the registry.

    Expected behavior:
    After adding the strategy group, get_groups() should return
    exactly that strategy group.
    """

    registry = StrategyRegistry()

    group = StrategyGroup(
        strategy_type="EMA",
        symbol="NIFTY",
        timeframe="5m",
        parameters=(("period", 10),),
    )

    registry.add_group(group)

    assert registry.get_groups() == {group}


def test_add_multiple_strategies():
    """
    Test Case:
    Verify that multiple different strategy groups can be registered.

    Expected behavior:
    All added strategy groups should be present in the registry.
    """

    registry = StrategyRegistry()

    ema_nifty = StrategyGroup(
        strategy_type="EMA",
        symbol="NIFTY",
        timeframe="5m",
        parameters=(("period", 10),),
    )

    ema_reliance = StrategyGroup(
        strategy_type="EMA",
        symbol="RELIANCE",
        timeframe="5m",
        parameters=(("period", 10),),
    )

    registry.add_group(ema_nifty)
    registry.add_group(ema_reliance)

    assert registry.get_groups() == {
        ema_nifty,
        ema_reliance,
    }


def test_duplicate_strategy_is_registered_only_once():
    """
    Test Case:
    Verify that registering the same strategy group more than once
    does not create duplicate entries.

    Expected behavior:
    The registry should contain only one instance of the
    logically identical strategy group.
    """

    registry = StrategyRegistry()

    group1 = StrategyGroup(
        strategy_type="EMA",
        symbol="NIFTY",
        timeframe="5m",
        parameters=(("period", 10),),
    )

    group2 = StrategyGroup(
        strategy_type="EMA",
        symbol="NIFTY",
        timeframe="5m",
        parameters=(("period", 10),),
    )

    registry.add_group(group1)
    registry.add_group(group2)

    assert len(registry.get_groups()) == 1


def test_different_parameters_create_different_groups():
    """
    Test Case:
    Verify that strategy groups with different parameters are treated
    as different strategy groups.

    Expected behavior:
    EMA(10) and EMA(20) should both exist in the registry.
    """

    registry = StrategyRegistry()

    ema_10 = StrategyGroup(
        strategy_type="EMA",
        symbol="NIFTY",
        timeframe="5m",
        parameters=(("period", 10),),
    )

    ema_20 = StrategyGroup(
        strategy_type="EMA",
        symbol="NIFTY",
        timeframe="5m",
        parameters=(("period", 20),),
    )

    registry.add_group(ema_10)
    registry.add_group(ema_20)

    assert len(registry.get_groups()) == 2


def test_remove_strategy():
    """
    Test Case:
    Verify that an existing strategy group can be removed.

    Expected behavior:
    After removal, the strategy group should no longer exist
    in the registry.
    """

    registry = StrategyRegistry()

    group = StrategyGroup(
        strategy_type="EMA",
        symbol="NIFTY",
        timeframe="5m",
        parameters=(("period", 10),),
    )

    registry.add_group(group)
    registry.remove_group(group)

    assert registry.get_groups() == set()


def test_remove_non_existing_strategy():
    """
    Test Case:
    Verify that attempting to remove a strategy group that is not
    registered does not cause an error or change the registry.

    Expected behavior:
    The registry should remain empty.
    """

    registry = StrategyRegistry()

    group = StrategyGroup(
        strategy_type="EMA",
        symbol="NIFTY",
        timeframe="5m",
        parameters=(("period", 10),),
    )

    registry.remove_group(group)

    assert registry.get_groups() == set()


def test_get_strategies_returns_copy():
    """
    Test Case:
    Verify that get_groups() returns a copy of the internal registry
    rather than exposing the internal set directly.

    Expected behavior:
    Clearing the returned set must not modify the actual registry.
    """

    registry = StrategyRegistry()

    group = StrategyGroup(
        strategy_type="EMA",
        symbol="NIFTY",
        timeframe="5m",
        parameters=(("period", 10),),
    )

    registry.add_group(group)

    groups = registry.get_groups()

    # Modify the returned set.
    groups.clear()

    # The original registry should remain unchanged.
    assert registry.get_groups() == {group} 