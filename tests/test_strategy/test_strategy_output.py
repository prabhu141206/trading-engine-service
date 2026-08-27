from datetime import datetime

from strategy.strategy_models import StrategyGroup
from strategy.strategy_output import (
    SignalSide,
    SignalType,
    StrategyOutput,
)


def test_entry_output():
    """
    Verify that a strategy can generate an ENTRY signal.

    The strategy output represents only the strategy's decision.
    It does not contain user, risk, or order-execution information.
    """

    timestamp = datetime.now()

    group = StrategyGroup(
        strategy_type="EMA",
        symbol="NIFTY",
        timeframe="5m",
        parameters=(("period", 10),),
    )

    output = StrategyOutput(
        strategy_group=group,
        signal_type=SignalType.ENTRY,
        side=SignalSide.BUY,
        timestamp=timestamp,
    )

    # The output must preserve the exact strategy computation identity.
    assert output.strategy_group == group

    # The signal must represent an ENTRY decision.
    assert output.signal_type == SignalType.ENTRY

    # The ENTRY is a BUY signal.
    assert output.side == SignalSide.BUY

    # The output must preserve the generation timestamp.
    assert output.timestamp == timestamp


def test_exit_output():
    """
    Verify that a strategy can generate an EXIT signal.

    EXIT signals are separate from ENTRY signals and represent the
    strategy's decision to leave an existing trade/setup.
    """

    timestamp = datetime.now()

    group = StrategyGroup(
        strategy_type="EMA",
        symbol="NIFTY",
        timeframe="5m",
        parameters=(("period", 10),),
    )

    output = StrategyOutput(
        strategy_group=group,
        signal_type=SignalType.EXIT,
        side=SignalSide.SELL,
        timestamp=timestamp,
    )

    # The output must preserve the exact strategy computation identity.
    assert output.strategy_group == group

    # The signal must represent an EXIT decision.
    assert output.signal_type == SignalType.EXIT

    # The EXIT is a SELL signal.
    assert output.side == SignalSide.SELL

    # The output must preserve the generation timestamp.
    assert output.timestamp == timestamp