from strategy.strategy_requirements import StrategyRequirements


def test_default_requirements():
    """
    Verify that a strategy can be created with no data requirements.

    This represents the default state where the strategy does not
    require candles, indicators, or tick data.
    """
    requirements = StrategyRequirements()

    assert requirements.candle_timeframes == ()
    assert requirements.indicators == ()
    assert requirements.requires_ticks is False


def test_ema_requirements():
    """
    Verify that a strategy can explicitly declare its required data.

    EMA currently requires:
        - 5-minute candles
        - EMA 10 indicator
        - continuous tick data
    """
    requirements = StrategyRequirements(
        candle_timeframes=("5m",),
        indicators=("EMA_10",),
        requires_ticks=True,
    )

    assert requirements.candle_timeframes == ("5m",)
    assert requirements.indicators == ("EMA_10",)
    assert requirements.requires_ticks is True


def test_requirements_are_immutable():
    """
    Verify that strategy requirements cannot be modified after creation.

    Requirements represent the contract of a strategy and should remain
    stable while the strategy is running.
    """
    requirements = StrategyRequirements(
        candle_timeframes=("5m",),
        indicators=("EMA_10",),
        requires_ticks=True,
    )

    try:
        requirements.requires_ticks = False
        assert False
    except AttributeError:
        pass