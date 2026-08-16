from registry.strategy_models import StrategyGroup
from registry.strategy_registry import StrategyRegistry


def test_add_strategy():
    registry = StrategyRegistry()

    group = StrategyGroup(
        strategy_type="EMA",
        symbol="NIFTY",
        timeframe="5m",
        parameters=(("period", 10),)
    )

    registry.add_strategy(group)

    assert registry.get_strategies() == {group}


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

    registry.add_strategy(ema_nifty)
    registry.add_strategy(ema_reliance)

    assert registry.get_strategies() == {
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

    registry.add_strategy(group1)
    registry.add_strategy(group2)

    assert len(registry.get_strategies()) == 1


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

    registry.add_strategy(ema_10)
    registry.add_strategy(ema_20)

    assert len(registry.get_strategies()) == 2


def test_remove_strategy():
    registry = StrategyRegistry()

    group = StrategyGroup(
        strategy_type="EMA",
        symbol="NIFTY",
        timeframe="5m",
        parameters=(("period", 10),)
    )

    registry.add_strategy(group)
    registry.remove_strategy(group)

    assert registry.get_strategies() == set()


def test_remove_non_existing_strategy():
    registry = StrategyRegistry()

    group = StrategyGroup(
        strategy_type="EMA",
        symbol="NIFTY",
        timeframe="5m",
        parameters=(("period", 10),)
    )

    registry.remove_strategy(group)

    assert registry.get_strategies() == set()


def test_get_strategies_returns_copy():
    registry = StrategyRegistry()

    group = StrategyGroup(
        strategy_type="EMA",
        symbol="NIFTY",
        timeframe="5m",
        parameters=(("period", 10),)
    )

    registry.add_strategy(group)

    strategies = registry.get_strategies()
    strategies.clear()

    assert registry.get_strategies() == {group}