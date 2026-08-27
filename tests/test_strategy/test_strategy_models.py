from strategy.strategy_models import StrategyGroup


def test_identical_strategy_groups_are_equal():
    """
    Verify that two StrategyGroup objects with exactly the same
    configuration are considered identical.

    This is critical because StrategyRegistry uses a set to remove
    duplicate strategy configurations.
    """
    first = StrategyGroup(
        strategy_type="EMA",
        symbol="NIFTY",
        timeframe="5m",
        parameters=(("period", 10),),
    )

    second = StrategyGroup(
        strategy_type="EMA",
        symbol="NIFTY",
        timeframe="5m",
        parameters=(("period", 10),),
    )

    assert first == second
    assert hash(first) == hash(second)


def test_different_parameters_create_different_groups():
    """
    Verify that changing a strategy parameter creates a different
    strategy group.

    EMA 10 and EMA 20 must be treated as separate configurations.
    """
    first = StrategyGroup(
        strategy_type="EMA",
        symbol="NIFTY",
        timeframe="5m",
        parameters=(("period", 10),),
    )

    second = StrategyGroup(
        strategy_type="EMA",
        symbol="NIFTY",
        timeframe="5m",
        parameters=(("period", 20),),
    )

    assert first != second


def test_different_symbols_create_different_groups():
    """
    Verify that the same strategy applied to different symbols creates
    different strategy groups.

    EMA + NIFTY and EMA + RELIANCE must have independent strategy
    instances later.
    """
    nifty = StrategyGroup(
        strategy_type="EMA",
        symbol="NIFTY",
        timeframe="5m",
        parameters=(("period", 10),),
    )

    reliance = StrategyGroup(
        strategy_type="EMA",
        symbol="RELIANCE",
        timeframe="5m",
        parameters=(("period", 10),),
    )

    assert nifty != reliance