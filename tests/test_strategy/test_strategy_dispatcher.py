from datetime import datetime

from strategy.strategy_context import StrategyContext
from strategy.strategy_dispatcher import StrategyDispatcher
from strategy.strategy_models import StrategyType
from strategy.strategy_output import StrategyOutput
from strategy.strategy_requirements import StrategyRequirements
from strategy.strategy_state import StrategyState


class FakeStrategy:
    """
    Minimal strategy implementation used only for dispatcher tests.

    It records every context and tick received so the tests can verify
    whether the dispatcher routed data correctly.
    """

    def __init__(
        self,
        strategy_type: StrategyType,
        symbol: str,
        timeframe: str,
        candle_timeframes: tuple[str, ...],
        requires_ticks: bool,
    ) -> None:
        self.strategy_type = strategy_type
        self.symbol = symbol
        self.timeframe = timeframe
        self._requirements = StrategyRequirements(
            candle_timeframes=candle_timeframes,
            requires_ticks=requires_ticks,
        )

        self.received_contexts = []
        self.received_ticks = []

        self.state = StrategyState.IDLE

    def get_requirements(self) -> StrategyRequirements:
        """Return the data requirements used by the dispatcher."""
        return self._requirements

    def on_context(
        self,
        context: StrategyContext,
    ) -> StrategyOutput | None:
        """Record a context received from the dispatcher."""
        self.received_contexts.append(context)
        return None

    def on_tick(
        self,
        context: StrategyContext,
    ) -> StrategyOutput | None:
        """Record a tick context received from the dispatcher."""
        self.received_ticks.append(context)
        return None


def create_context(
    symbol: str,
    timeframe: str,
) -> StrategyContext:
    """
    Create a minimal StrategyContext for dispatcher tests.

    The context represents one concrete market interval.
    """
    start_time = datetime(2026, 8, 23, 10, 15)
    end_time = datetime(2026, 8, 23, 10, 20)

    return StrategyContext(
        symbol=symbol,
        timeframe=timeframe,
        start_time=start_time,
        end_time=end_time,
    )


def create_ema_nifty() -> FakeStrategy:
    """
    Create an EMA strategy operating on NIFTY 5m data.

    EMA requires continuous tick data.
    """
    return FakeStrategy(
        strategy_type=StrategyType.EMA,
        symbol="NIFTY",
        timeframe="5m",
        candle_timeframes=("5m",),
        requires_ticks=True,
    )


def create_vwap_nifty() -> FakeStrategy:
    """
    Create a VWAP strategy operating on NIFTY 15m data.

    VWAP does not require tick data.
    """
    return FakeStrategy(
        strategy_type=StrategyType.VWAP,
        symbol="NIFTY",
        timeframe="15m",
        candle_timeframes=("15m",),
        requires_ticks=False,
    )


def create_ema_reliance() -> FakeStrategy:
    """
    Create an EMA strategy operating on RELIANCE 5m data.
    """
    return FakeStrategy(
        strategy_type=StrategyType.EMA,
        symbol="RELIANCE",
        timeframe="5m",
        candle_timeframes=("5m",),
        requires_ticks=True,
    )


def test_5m_context_routes_to_ema_nifty():
    """
    Verify that a NIFTY 5m context reaches the EMA + NIFTY strategy.

    The strategy explicitly requires 5m candle data for NIFTY.
    """
    ema_nifty = create_ema_nifty()
    dispatcher = StrategyDispatcher([ema_nifty])

    context = create_context("NIFTY", "5m")

    dispatcher.dispatch_context(context)

    assert ema_nifty.received_contexts == [context]


def test_15m_context_routes_to_vwap_nifty():
    """
    Verify that a NIFTY 15m context reaches the VWAP + NIFTY strategy.
    """
    vwap_nifty = create_vwap_nifty()
    dispatcher = StrategyDispatcher([vwap_nifty])

    context = create_context("NIFTY", "15m")

    dispatcher.dispatch_context(context)

    assert vwap_nifty.received_contexts == [context]


def test_wrong_timeframe_is_not_routed():
    """
    Verify that a strategy does not receive a context for a timeframe
    it did not declare as a requirement.

    VWAP requires 15m, so a NIFTY 5m context must not reach it.
    """
    vwap_nifty = create_vwap_nifty()
    dispatcher = StrategyDispatcher([vwap_nifty])

    context = create_context("NIFTY", "5m")

    dispatcher.dispatch_context(context)

    assert vwap_nifty.received_contexts == []


def test_wrong_symbol_is_not_routed():
    """
    Verify that a strategy receives data only for its configured symbol.

    EMA + RELIANCE must not receive a NIFTY context even though both
    strategies use the same 5m timeframe.
    """
    ema_reliance = create_ema_reliance()
    dispatcher = StrategyDispatcher([ema_reliance])

    context = create_context("NIFTY", "5m")

    dispatcher.dispatch_context(context)

    assert ema_reliance.received_contexts == []


def test_same_symbol_different_strategies_are_routed_independently():
    """
    Verify that multiple strategies can operate on the same symbol
    while consuming different timeframes.

    EMA + NIFTY receives 5m data.
    VWAP + NIFTY receives 15m data.
    """
    ema_nifty = create_ema_nifty()
    vwap_nifty = create_vwap_nifty()

    dispatcher = StrategyDispatcher(
        [
            ema_nifty,
            vwap_nifty,
        ]
    )

    five_minute_context = create_context("NIFTY", "5m")
    fifteen_minute_context = create_context("NIFTY", "15m")

    dispatcher.dispatch_context(five_minute_context)
    dispatcher.dispatch_context(fifteen_minute_context)

    assert ema_nifty.received_contexts == [
        five_minute_context
    ]

    assert vwap_nifty.received_contexts == [
        fifteen_minute_context
    ]


def test_tick_routes_to_strategy_requiring_ticks():
    """
    Verify that tick data reaches a strategy whose requirements declare
    requires_ticks=True.
    """
    ema_nifty = create_ema_nifty()
    dispatcher = StrategyDispatcher([ema_nifty])

    tick_context = create_context("NIFTY", "5m")

    dispatcher.dispatch_tick(tick_context)

    assert ema_nifty.received_ticks == [tick_context]


def test_tick_does_not_route_to_strategy_not_requiring_ticks():
    """
    Verify that tick data is not sent to strategies that explicitly
    declare that they do not require ticks.
    """
    vwap_nifty = create_vwap_nifty()
    dispatcher = StrategyDispatcher([vwap_nifty])

    tick_context = create_context("NIFTY", "15m")

    dispatcher.dispatch_tick(tick_context)

    assert vwap_nifty.received_ticks == []


def test_tick_routes_only_to_matching_symbol():
    """
    Verify that tick routing is isolated by symbol.

    A NIFTY tick must not reach the EMA + RELIANCE strategy.
    """
    ema_reliance = create_ema_reliance()
    dispatcher = StrategyDispatcher([ema_reliance])

    tick_context = create_context("NIFTY", "5m")

    dispatcher.dispatch_tick(tick_context)

    assert ema_reliance.received_ticks == []


def test_multiple_tick_strategies_on_same_symbol_receive_tick():
    """
    Verify that all tick-consuming strategies for the same symbol
    receive the tick.

    This is important because multiple strategies may operate on the
    same underlying symbol in the future.
    """
    ema_nifty_one = create_ema_nifty()
    ema_nifty_two = create_ema_nifty()

    dispatcher = StrategyDispatcher(
        [
            ema_nifty_one,
            ema_nifty_two,
        ]
    )

    tick_context = create_context("NIFTY", "5m")

    dispatcher.dispatch_tick(tick_context)

    assert ema_nifty_one.received_ticks == [tick_context]
    assert ema_nifty_two.received_ticks == [tick_context]