import pytest

from strategy.strategy_factory import StrategyFactory
from strategy.strategy_models import StrategyGroup, StrategyType
from strategy.strategies.ema_strategy import EMAStrategy


def create_ema_group(
    symbol: str = "NIFTY",
    timeframe: str = "5m",
) -> StrategyGroup:
    """
    Create a standard EMA StrategyGroup for factory tests.
    """
    return StrategyGroup(
        strategy_type=StrategyType.EMA,
        symbol=symbol,
        timeframe=timeframe,
        parameters=(("period", 10),),
    )


def test_factory_creates_ema_strategy():
    """
    Verify that the factory converts an EMA StrategyGroup into
    the correct concrete EMAStrategy object.
    """
    factory = StrategyFactory()
    group = create_ema_group()

    strategy = factory.create(group)

    assert isinstance(strategy, EMAStrategy)


def test_factory_passes_configuration_to_strategy():
    """
    Verify that the factory correctly transfers the StrategyGroup
    configuration into the created strategy instance.
    """
    factory = StrategyFactory()

    group = create_ema_group(
        symbol="RELIANCE",
        timeframe="5m",
    )

    strategy = factory.create(group)

    assert strategy.symbol == "RELIANCE"
    assert strategy.timeframe == "5m"
    assert strategy.parameters == (("period", 10),)


def test_factory_creates_independent_strategy_instances():
    """
    Verify that creating two different StrategyGroups produces
    independent strategy objects with independent runtime state.
    """
    factory = StrategyFactory()

    nifty_group = create_ema_group("NIFTY")
    reliance_group = create_ema_group("RELIANCE")

    nifty_strategy = factory.create(nifty_group)
    reliance_strategy = factory.create(reliance_group)

    assert nifty_strategy is not reliance_strategy
    assert nifty_strategy.symbol == "NIFTY"
    assert reliance_strategy.symbol == "RELIANCE"


def test_factory_rejects_unsupported_strategy():
    """
    Verify that the factory explicitly rejects strategy types that
    do not have a registered concrete implementation.
    """
    factory = StrategyFactory()

    unsupported_group = StrategyGroup(
        strategy_type="UNKNOWN",
        symbol="NIFTY",
        timeframe="5m",
        parameters=(),
    )

    with pytest.raises(ValueError, match="Unsupported strategy type"):
        factory.create(unsupported_group)