from candle.candle_models import Candle

from strategy.strategy_context import StrategyContext
from strategy.strategy_models import StrategyGroup
from strategy.strategy_output import (
    SignalSide,
    SignalType,
    StrategyOutput,
)
from strategy.strategy_requirements import StrategyRequirements
from strategy.strategy_state import (
    StrategyState,
    TradeDirection,
)


class EMAStrategy:
    """
    EMA 10 strategy.

    Current strategy rules:

    Long setup:
        - Bearish candle.
        - Candle does not touch EMA 10.
        - Arm the trigger.
        - Tick breaks trigger candle high.
        - Generate BUY entry.
        - Enter IN_TRADE.

    Short setup:
        - Bullish candle.
        - Candle does not touch EMA 10.
        - Arm the trigger.
        - Tick breaks trigger candle low.
        - Generate SELL entry.
        - Enter IN_TRADE.

    Exit:
        - Long trade exits when a candle closes below EMA 10.
        - Short trade exits when a candle closes above EMA 10.

    Trend detection is intentionally not implemented because the
    current strategy specification does not define a trend rule.
    """

    def __init__(
        self,
        symbol: str,
        timeframe: str,
        parameters: tuple[tuple[str, object], ...],
    ) -> None:
        self.symbol = symbol
        self.timeframe = timeframe
        self.parameters = parameters

        # This uniquely identifies the strategy computation.
        self.strategy_group = StrategyGroup(
            strategy_type="EMA",
            symbol=self.symbol,
            timeframe=self.timeframe,
            parameters=self.parameters,
        )

        self.state = StrategyState.IDLE

        self._trigger_candle: Candle | None = None
        self._direction: TradeDirection | None = None

    # ---------------------------------------------------------
    # Requirements
    # ---------------------------------------------------------

    def get_requirements(self) -> StrategyRequirements:
        """
        Return the market-data requirements of the EMA strategy.
        """
        return StrategyRequirements(
            candle_timeframes=(self.timeframe,),
            indicators=("EMA_10",),
            requires_ticks=True,
        )

    # ---------------------------------------------------------
    # Context
    # ---------------------------------------------------------

    def on_context(
        self,
        context: StrategyContext,
    ) -> StrategyOutput | None:
        """
        Process a completed candle + indicator context.

        Candle events are responsible for:
            - creating a trigger
            - checking trade exits

        Tick events are responsible for:
            - confirming trigger breakouts
        """

        candle = context.candle

        if candle is None:
            return None

        ema_10 = self._get_ema(context)

        if ema_10 is None:
            return None

        # -----------------------------------------------------
        # IN_TRADE
        # -----------------------------------------------------

        if self.state is StrategyState.IN_TRADE:
            return self._check_exit(
                candle=candle,
                ema_10=ema_10,
                context=context,
            )

        # -----------------------------------------------------
        # TRIGGER_ARMED
        # -----------------------------------------------------

        if self.state is StrategyState.TRIGGER_ARMED:
            return None

        # -----------------------------------------------------
        # IDLE
        # -----------------------------------------------------

        if self.state is StrategyState.IDLE:
            return self._check_trigger(
                candle=candle,
                ema_10=ema_10,
            )

        return None

    # ---------------------------------------------------------
    # Tick
    # ---------------------------------------------------------

    def on_tick(
        self,
        context: StrategyContext,
    ) -> StrategyOutput | None:
        """
        Process tick data.

        Ticks matter only while a trigger is armed.
        """

        if self.state is not StrategyState.TRIGGER_ARMED:
            return None

        if context.tick is None:
            return None

        if self._trigger_candle is None:
            return None

        tick_price = self._get_tick_price(context)

        if tick_price is None:
            return None

        # -----------------------------------------------------
        # LONG BREAKOUT
        # -----------------------------------------------------

        if (
            self._direction is TradeDirection.LONG
            and tick_price > self._trigger_candle.high
        ):
            self.state = StrategyState.IN_TRADE

            return StrategyOutput(
                strategy_group=self.strategy_group,
                signal_type=SignalType.ENTRY,
                side=SignalSide.BUY,
                timestamp=context.end_time,
            )

        # -----------------------------------------------------
        # SHORT BREAKOUT
        # -----------------------------------------------------

        if (
            self._direction is TradeDirection.SHORT
            and tick_price < self._trigger_candle.low
        ):
            self.state = StrategyState.IN_TRADE

            return StrategyOutput(
                strategy_group=self.strategy_group,
                signal_type=SignalType.ENTRY,
                side=SignalSide.SELL,
                timestamp=context.end_time,
            )

        return None

    # ---------------------------------------------------------
    # Trigger
    # ---------------------------------------------------------

    def _check_trigger(
        self,
        candle: Candle,
        ema_10: float,
    ) -> StrategyOutput | None:
        """
        Check whether the completed candle creates a valid trigger.

        Red candle:
            candle.close < candle.open

        Green candle:
            candle.close > candle.open

        The candle must be completely away from EMA 10.
        """

        if self._touches_ema(
            candle,
            ema_10,
        ):
            return None

        # Red candle → LONG setup.
        if candle.close < candle.open:
            self._trigger_candle = candle
            self._direction = TradeDirection.LONG
            self.state = StrategyState.TRIGGER_ARMED

            return None

        # Green candle → SHORT setup.
        if candle.close > candle.open:
            self._trigger_candle = candle
            self._direction = TradeDirection.SHORT
            self.state = StrategyState.TRIGGER_ARMED

            return None

        return None

    # ---------------------------------------------------------
    # Exit
    # ---------------------------------------------------------

    def _check_exit(
        self,
        candle: Candle,
        ema_10: float,
        context: StrategyContext,
    ) -> StrategyOutput | None:
        """
        Check the strategy exit condition.
        """

        # Long trade:
        # candle closes below EMA 10.
        if (
            self._direction is TradeDirection.LONG
            and candle.close < ema_10
        ):
            return self._exit(
                context=context,
                side=SignalSide.SELL,
            )

        # Short trade:
        # candle closes above EMA 10.
        if (
            self._direction is TradeDirection.SHORT
            and candle.close > ema_10
        ):
            return self._exit(
                context=context,
                side=SignalSide.BUY,
            )

        return None

    def _exit(
        self,
        context: StrategyContext,
        side: SignalSide,
    ) -> StrategyOutput:
        """
        Generate an exit signal and reset strategy state.
        """

        output = StrategyOutput(
            strategy_group=self.strategy_group,
            signal_type=SignalType.EXIT,
            side=side,
            timestamp=context.end_time,
        )

        self.state = StrategyState.IDLE
        self._trigger_candle = None
        self._direction = None

        return output

    # ---------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------

    @staticmethod
    def _touches_ema(
        candle: Candle,
        ema_10: float,
    ) -> bool:
        """
        Determine whether EMA 10 touches the candle range.

        EMA touches the candle when it lies between the candle's
        low and high, inclusive.
        """
        return (
            candle.low
            <= ema_10
            <= candle.high
        )

    @staticmethod
    def _get_ema(
        context: StrategyContext,
    ) -> float | None:
        """
        Extract EMA 10 from the strategy context.
        """

        if not context.indicators:
            return None

        value = context.indicators.get(
            "EMA_10"
        )

        if value is None:
            return None

        return float(value)

    @staticmethod
    def _get_tick_price(
        context: StrategyContext,
    ) -> float | None:
        """
        Extract the price from the tick payload.

        The exact tick model is not yet part of this strategy contract,
        so this currently supports a numeric tick or an object exposing
        a `price` attribute.
        """

        tick = context.tick

        if isinstance(tick, (int, float)):
            return float(tick)

        price = getattr(
            tick,
            "price",
            None,
        )

        if price is None:
            return None

        return float(price)