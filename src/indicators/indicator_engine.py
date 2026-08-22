from candle.candle_models import CandleBatch
from candle.candle_timeframe import CandleTimeframe

from event_system.event import Event
from event_system.event_bus import EventBus
from event_system.event_type import EventType

from indicators.active_symbol_provider import ActiveSymbolProvider
from indicators.ema_calculator import EMACalculator
from indicators.historical_data_provider import HistoricalCandleProvider
from indicators.indicator_models import (
    IndicatorBatch,
    SymbolIndicatorState,
)
from indicators.indicator_state import IndicatorStateStore


class IndicatorEngine:
    """
    Coordinates indicator initialization and live updates.

    Responsibilities:
        - Warm up EMA 10 from historical candles.
        - Maintain the latest indicator state.
        - Receive completed CandleBatch events.
        - Update EMA 10 for each symbol.
        - Publish IndicatorBatch events.
    """

    def __init__(
        self,
        event_bus: EventBus,
        symbol_provider: ActiveSymbolProvider,
        historical_provider: HistoricalCandleProvider,
        state_store: IndicatorStateStore,
    ) -> None:

        self._event_bus = event_bus
        self._symbol_provider = symbol_provider
        self._historical_provider = historical_provider
        self._state_store = state_store

        self._ema_calculator = EMACalculator(
            period=10,
        )

        self._timeframe = (
            CandleTimeframe.FIVE_MINUTES.value
        )

        self._warmup_limit = 50

    # ---------------------------------------------------------
    # Lifecycle
    # ---------------------------------------------------------

    def start(self) -> None:
        """
        Warm up indicators and subscribe to live candle batches.
        """

        self._warmup()

        self._event_bus.subscribe(
            EventType.CANDLE_BATCH_CLOSED,
            self._on_candle_batch,
        )

    # ---------------------------------------------------------
    # Warm-up
    # ---------------------------------------------------------

    def _warmup(self) -> None:
        """
        Initialize EMA 10 for every active symbol.
        """

        symbols = (
            self._symbol_provider.get_active_symbols()
        )

        for symbol in symbols:
            self._warmup_symbol(symbol)

    def _warmup_symbol(
        self,
        symbol: str,
    ) -> None:

        candles = (
            self._historical_provider
            .get_historical_candles(
                symbol=symbol,
                timeframe=self._timeframe,
                limit=self._warmup_limit,
            )
        )

        if len(candles) < self._warmup_limit:
            raise ValueError(
                f"Insufficient historical candles "
                f"for {symbol}. "
                f"Required: {self._warmup_limit}, "
                f"received: {len(candles)}."
            )

        closes = [
            candle.close
            for candle in candles
        ]

        ema_10 = (
            self._ema_calculator
            .calculate_from_closes(closes)
        )

        self._state_store.set(
            SymbolIndicatorState(
                symbol=symbol,
                timeframe=self._timeframe,
                ema_10=ema_10,
                ready=True,
            )
        )

    # ---------------------------------------------------------
    # Event Handler
    # ---------------------------------------------------------

    def _on_candle_batch(
        self,
        event: Event,
    ) -> None:
        """
        Process one completed CandleBatch.
        """

        batch: CandleBatch = event.payload

        self._process_candle_batch(batch)

    # ---------------------------------------------------------
    # Live Indicator Update
    # ---------------------------------------------------------

    def _process_candle_batch(
        self,
        batch: CandleBatch,
    ) -> None:
        """
        Update EMA 10 for every symbol in the batch.
        """

        updated_indicators: dict[
            str,
            SymbolIndicatorState,
        ] = {}

        for symbol, candle in batch.candles.items():

            state = self._state_store.get(
                symbol,
                batch.timeframe,
            )

            if state is None or not state.ready:
                raise ValueError(
                    f"Indicator state is not initialized "
                    f"for {symbol}."
                )

            new_ema = (
                self._ema_calculator.update(
                    previous_ema=state.ema_10,
                    close=candle.close,
                )
            )

            updated_state = SymbolIndicatorState(
                symbol=symbol,
                timeframe=batch.timeframe,
                ema_10=new_ema,
                ready=True,
            )

            self._state_store.set(
                updated_state
            )

            updated_indicators[symbol] = (
                updated_state
            )

        if not updated_indicators:
            return

        indicator_batch = IndicatorBatch(
            timeframe=batch.timeframe,
            start_time=batch.start_time,
            end_time=batch.end_time,
            indicators=updated_indicators,
        )

        self._event_bus.publish(
            Event(
                event_type=(
                    EventType.INDICATOR_BATCH_UPDATED
                ),
                payload=indicator_batch,
            )
        )