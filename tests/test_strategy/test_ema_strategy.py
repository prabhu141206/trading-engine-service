from datetime import datetime

from candle.candle_models import Candle
from strategy.strategy_context import StrategyContext
from strategy.strategy_models import StrategyType
from strategy.strategy_state import (
    StrategyState,
    TradeDirection,
)
from strategy.strategies.ema_strategy import EMAStrategy


def create_strategy() -> EMAStrategy:
    """
    Create a standard EMA 10 strategy instance for testing.
    """
    return EMAStrategy(
        symbol="NIFTY",
        timeframe="5m",
        parameters=(("period", 10),),
    )


def create_candle(
    open_price: float,
    high: float,
    low: float,
    close: float,
) -> Candle:
    """
    Create a candle for the fixed 5-minute test interval.
    """
    return Candle(
        symbol="NIFTY",
        timeframe="5m",
        start_time=datetime(2026, 8, 24, 10, 15),
        end_time=datetime(2026, 8, 24, 10, 20),
        open=open_price,
        high=high,
        low=low,
        close=close,
    )


def create_context(
    candle: Candle,
    ema: float,
    tick=None,
) -> StrategyContext:
    """
    Create a StrategyContext containing candle, EMA and optional tick.
    """
    return StrategyContext(
        symbol="NIFTY",
        timeframe="5m",
        start_time=candle.start_time,
        end_time=candle.end_time,
        candle=candle,
        indicators={
            "EMA_10": ema,
        },
        tick=tick,
    )


def test_new_strategy_starts_idle():
    """
    Verify that a newly created EMA strategy starts in IDLE.
    """
    strategy = create_strategy()

    # A newly created strategy must not have an active setup.
    assert strategy.state is StrategyState.IDLE


def test_red_candle_away_from_ema_arms_long_trigger():
    """
    Verify that a red candle completely above EMA 10 creates
    a long trigger.

    The strategy should move from IDLE to TRIGGER_ARMED and
    remember the LONG direction.
    """
    strategy = create_strategy()

    candle = create_candle(
        open_price=105.0,
        high=108.0,
        low=103.0,
        close=104.0,
    )

    context = create_context(
        candle=candle,
        ema=100.0,
    )

    output = strategy.on_context(context)

    # Trigger candles do not immediately generate a signal.
    assert output is None

    # The strategy must now wait for a bullish breakout.
    assert strategy.state is StrategyState.TRIGGER_ARMED

    # The candle above EMA arms a LONG setup.
    assert strategy._direction is TradeDirection.LONG

    # The trigger candle must be remembered.
    assert strategy._trigger_candle == candle


def test_green_candle_away_from_ema_arms_short_trigger():
    """
    Verify that a green candle completely below EMA 10 creates
    a short trigger.

    The strategy should move from IDLE to TRIGGER_ARMED and
    remember the SHORT direction.
    """
    strategy = create_strategy()

    candle = create_candle(
        open_price=95.0,
        high=97.0,
        low=92.0,
        close=96.0,
    )

    context = create_context(
        candle=candle,
        ema=100.0,
    )

    output = strategy.on_context(context)

    # Trigger candles do not immediately generate a signal.
    assert output is None

    # The strategy must wait for a bearish breakout.
    assert strategy.state is StrategyState.TRIGGER_ARMED

    # The candle below EMA arms a SHORT setup.
    assert strategy._direction is TradeDirection.SHORT

    # The trigger candle must be remembered.
    assert strategy._trigger_candle == candle


def test_candle_touching_ema_does_not_arm_trigger():
    """
    Verify that a candle touching EMA 10 is rejected.

    The strategy must remain IDLE.
    """
    strategy = create_strategy()

    candle = create_candle(
        open_price=105.0,
        high=108.0,
        low=100.0,
        close=104.0,
    )

    context = create_context(
        candle=candle,
        ema=100.0,
    )

    output = strategy.on_context(context)

    # A candle touching EMA is not a valid trigger.
    assert output is None

    # No setup should be created.
    assert strategy.state is StrategyState.IDLE
    assert strategy._direction is None
    assert strategy._trigger_candle is None


def test_long_trigger_breakout_generates_buy_entry():
    """
    Verify that a tick breaking the long trigger candle high
    generates a BUY entry and moves the strategy into IN_TRADE.
    """
    strategy = create_strategy()

    trigger_candle = create_candle(
        open_price=105.0,
        high=108.0,
        low=103.0,
        close=104.0,
    )

    trigger_context = create_context(
        candle=trigger_candle,
        ema=100.0,
    )

    # First create the LONG trigger.
    strategy.on_context(trigger_context)

    breakout_context = create_context(
        candle=trigger_candle,
        ema=100.0,
        tick=108.1,
    )

    output = strategy.on_tick(breakout_context)

    # A breakout must generate a signal.
    assert output is not None

    # The signal must identify the exact strategy computation.
    assert output.strategy_group.strategy_type == "EMA"
    assert output.strategy_group.symbol == "NIFTY"
    assert output.strategy_group.timeframe == "5m"
    assert output.strategy_group.parameters == (("period", 10),)

    # The signal must be an ENTRY.
    assert output.signal_type == "ENTRY"

    # A LONG breakout produces a BUY signal.
    assert output.side == "BUY"

    # The strategy must now represent an active trade.
    assert strategy.state is StrategyState.IN_TRADE


def test_long_trigger_without_breakout_stays_armed():
    """
    Verify that a tick below the trigger candle high does not
    generate an entry.

    The strategy must remain TRIGGER_ARMED.
    """
    strategy = create_strategy()

    trigger_candle = create_candle(
        open_price=105.0,
        high=108.0,
        low=103.0,
        close=104.0,
    )

    trigger_context = create_context(
        candle=trigger_candle,
        ema=100.0,
    )

    # Create the LONG trigger.
    strategy.on_context(trigger_context)

    tick_context = create_context(
        candle=trigger_candle,
        ema=100.0,
        tick=107.9,
    )

    output = strategy.on_tick(tick_context)

    # No breakout means no signal.
    assert output is None

    # The setup must remain active.
    assert strategy.state is StrategyState.TRIGGER_ARMED


def test_short_trigger_breakout_generates_sell_entry():
    """
    Verify that a tick breaking the short trigger candle low
    generates a SELL entry and moves the strategy into IN_TRADE.
    """
    strategy = create_strategy()

    trigger_candle = create_candle(
        open_price=95.0,
        high=97.0,
        low=92.0,
        close=96.0,
    )

    trigger_context = create_context(
        candle=trigger_candle,
        ema=100.0,
    )

    # First create the SHORT trigger.
    strategy.on_context(trigger_context)

    breakout_context = create_context(
        candle=trigger_candle,
        ema=100.0,
        tick=91.9,
    )

    output = strategy.on_tick(breakout_context)

    # A breakout must generate a signal.
    assert output is not None

    # The signal must identify the exact strategy computation.
    assert output.strategy_group.strategy_type == "EMA"
    assert output.strategy_group.symbol == "NIFTY"
    assert output.strategy_group.timeframe == "5m"
    assert output.strategy_group.parameters == (("period", 10),)

    # The signal must be an ENTRY.
    assert output.signal_type == "ENTRY"

    # A SHORT breakout produces a SELL signal.
    assert output.side == "SELL"

    # The strategy must now represent an active trade.
    assert strategy.state is StrategyState.IN_TRADE


def test_tick_while_idle_is_ignored():
    """
    Verify that ticks are ignored while the strategy is IDLE.

    Tick processing only becomes relevant after a trigger is armed.
    """
    strategy = create_strategy()

    candle = create_candle(
        open_price=105.0,
        high=108.0,
        low=103.0,
        close=104.0,
    )

    context = create_context(
        candle=candle,
        ema=100.0,
        tick=110.0,
    )

    output = strategy.on_tick(context)

    # No trigger exists, so the tick cannot generate a signal.
    assert output is None

    # The strategy must remain idle.
    assert strategy.state is StrategyState.IDLE


def test_long_trade_exits_when_candle_closes_below_ema():
    """
    Verify the long exit condition.

    A long trade exits when a completed candle closes below EMA 10.
    """
    strategy = create_strategy()

    trigger_candle = create_candle(
        open_price=105.0,
        high=108.0,
        low=103.0,
        close=104.0,
    )

    # Create LONG trigger.
    strategy.on_context(
        create_context(
            candle=trigger_candle,
            ema=100.0,
        )
    )

    # Break the trigger and enter the trade.
    strategy.on_tick(
        create_context(
            candle=trigger_candle,
            ema=100.0,
            tick=108.1,
        )
    )

    exit_candle = create_candle(
        open_price=102.0,
        high=103.0,
        low=98.0,
        close=99.0,
    )

    output = strategy.on_context(
        create_context(
            candle=exit_candle,
            ema=100.0,
        )
    )

    # An exit condition must generate a signal.
    assert output is not None

    # The output must identify the same strategy computation.
    assert output.strategy_group.strategy_type == "EMA"
    assert output.strategy_group.symbol == "NIFTY"
    assert output.strategy_group.timeframe == "5m"
    assert output.strategy_group.parameters == (("period", 10),)

    # The signal must be an EXIT.
    assert output.signal_type == "EXIT"

    # A long position exits by SELLING.
    assert output.side == "SELL"

    # The strategy must return to IDLE.
    assert strategy.state is StrategyState.IDLE
    assert strategy._direction is None
    assert strategy._trigger_candle is None


def test_short_trade_exits_when_candle_closes_above_ema():
    """
    Verify the short exit condition.

    A short trade exits when a completed candle closes above EMA 10.
    """
    strategy = create_strategy()

    trigger_candle = create_candle(
        open_price=95.0,
        high=97.0,
        low=92.0,
        close=96.0,
    )

    # Create SHORT trigger.
    strategy.on_context(
        create_context(
            candle=trigger_candle,
            ema=100.0,
        )
    )

    # Break the trigger and enter the trade.
    strategy.on_tick(
        create_context(
            candle=trigger_candle,
            ema=100.0,
            tick=91.9,
        )
    )

    exit_candle = create_candle(
        open_price=98.0,
        high=103.0,
        low=97.0,
        close=101.0,
    )

    output = strategy.on_context(
        create_context(
            candle=exit_candle,
            ema=100.0,
        )
    )

    # An exit condition must generate a signal.
    assert output is not None

    # The output must identify the same strategy computation.
    assert output.strategy_group.strategy_type == "EMA"
    assert output.strategy_group.symbol == "NIFTY"
    assert output.strategy_group.timeframe == "5m"
    assert output.strategy_group.parameters == (("period", 10),)

    # The signal must be an EXIT.
    assert output.signal_type == "EXIT"

    # A short position exits by BUYING.
    assert output.side == "BUY"

    # The strategy must return to IDLE.
    assert strategy.state is StrategyState.IDLE
    assert strategy._direction is None
    assert strategy._trigger_candle is None


def test_strategy_ignores_new_trigger_while_in_trade():
    """
    Verify that while IN_TRADE, a new trigger candle does not
    overwrite the current trade state.

    Exit logic has priority while the strategy is in a trade.
    """
    strategy = create_strategy()

    trigger_candle = create_candle(
        open_price=105.0,
        high=108.0,
        low=103.0,
        close=104.0,
    )

    # Create LONG trigger.
    strategy.on_context(
        create_context(
            candle=trigger_candle,
            ema=100.0,
        )
    )

    # Enter the LONG trade.
    strategy.on_tick(
        create_context(
            candle=trigger_candle,
            ema=100.0,
            tick=108.1,
        )
    )

    # The strategy must now be in a trade.
    assert strategy.state is StrategyState.IN_TRADE

    new_candle = create_candle(
        open_price=110.0,
        high=112.0,
        low=109.0,
        close=111.0,
    )

    output = strategy.on_context(
        create_context(
            candle=new_candle,
            ema=100.0,
        )
    )

    # A new trigger must not generate another signal while in trade.
    assert output is None

    # The existing trade must remain active.
    assert strategy.state is StrategyState.IN_TRADE