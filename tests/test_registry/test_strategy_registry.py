

from strategy.strategy_models import StrategyGroup
from registry.strategy_registry import StrategyRegistry


def test_add_strategy():
    registry = StrategyRegistry()

    group = StrategyGroup(
        strategy_type="EMA",
        symbol="NIFTY",
        timeframe="5m",
        parameters=(("period", 10),)
    )

    registry.add_group(group)

    assert registry.get_groups() == {group}


def test_add_multiple_strategies():
    registry = StrategyRegistry()

    ema_nifty = StrategyGroup(
        strategy_type="EMA",
        symbol="NIFTY",
        timeframe="5m",
        parameters=(("period", 10),)
    )

    ema_reliance = StrategyGroup(
        strategy_type="EMA",
        symbol="RELIANCE",
        timeframe="5m",
        parameters=(("period", 10),)
    )

    registry.add_group(ema_nifty)
    registry.add_group(ema_reliance)

    assert registry.get_groups() == {
        ema_nifty,
        ema_reliance,
    }


def test_duplicate_strategy_is_registered_only_once():
    registry = StrategyRegistry()

    group1 = StrategyGroup(
        strategy_type="EMA",
        symbol="NIFTY",
        timeframe="5m",
        parameters=(("period", 10),)
    )

    group2 = StrategyGroup(
        strategy_type="EMA",
        symbol="NIFTY",
        timeframe="5m",
        parameters=(("period", 10),)
    )

    registry.add_group(group1)
    registry.add_group(group2)

    assert len(registry.get_groups()) == 1


def test_different_parameters_create_different_groups():
    registry = StrategyRegistry()

    ema_10 = StrategyGroup(
        strategy_type="EMA",
        symbol="NIFTY",
        timeframe="5m",
        parameters=(("period", 10),)
    )

    ema_20 = StrategyGroup(
        strategy_type="EMA",
        symbol="NIFTY",
        timeframe="5m",
        parameters=(("period", 20),)
    )

    registry.add_group(ema_10)
    registry.add_group(ema_20)

    assert len(registry.get_groups()) == 2


def test_remove_strategy():
    registry = StrategyRegistry()

    group = StrategyGroup(
        strategy_type="EMA",
        symbol="NIFTY",
        timeframe="5m",
        parameters=(("period", 10),)
    )

    registry.add_group(group)
    registry.remove_group(group)

    assert registry.get_groups() == set()


def test_remove_non_existing_strategy():
    registry = StrategyRegistry()

    group = StrategyGroup(
        strategy_type="EMA",
        symbol="NIFTY",
        timeframe="5m",
        parameters=(("period", 10),)
    )

    registry.remove_group(group)

    assert registry.get_groups() == set()


def test_get_strategies_returns_copy():
    registry = StrategyRegistry()

    group = StrategyGroup(
        strategy_type="EMA",
        symbol="NIFTY",
        timeframe="5m",
        parameters=(("period", 10),)
    )

    registry.add_group(group)

    groups = registry.get_groups()
    groups.clear()

    assert registry.get_groups() == {group}