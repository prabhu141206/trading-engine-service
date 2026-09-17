import threading
import time

from candle.candle_models import CandleBatch
from candle.candle_timeframe import CandleTimeframe

from event_system.event import Event
from event_system.event_bus import EventBus
from event_system.event_type import EventType

from indicators.active_symbol_provider import ActiveSymbolProvider
from indicators.ema_calculator import EMACalculator
from market_data.historical_data_provider import HistoricalCandleProvider
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
        self._max_warmup_retries = 5
        self._warmup_retry_delay = 30
        self._pending_batches: list[CandleBatch] = []
        self._warmup_thread: threading.Thread | None = None
    # ---------------------------------------------------------
    # Lifecycle
    # ---------------------------------------------------------

    def start(self) -> None:
        """
        Subscribe to lifecycle and market-data events.
        """

        self._event_bus.subscribe(
            EventType.SESSIONS_READY,
            self._on_sessions_ready,
        )

        self._event_bus.subscribe(
            EventType.CANDLE_BATCH_CLOSED,
            self._on_candle_batch,
        )

    def _on_sessions_ready(
        self,
        event: Event,
    ) -> None:
        """
        Warm up indicators after runtime session configuration
        has been loaded.
        """

        print("IndicatorEngine: SESSIONS_READY received")
        if self._warmup_thread is not None and self._warmup_thread.is_alive():
            print("IndicatorEngine: warm-up already running")
            return

        self._warmup_thread = threading.Thread(
            target=self._warmup,
            daemon=True,
        )

        self._warmup_thread.start()

        print("IndicatorEngine: historical warm-up started in background")
    # ---------------------------------------------------------
    # Warm-up
    # ---------------------------------------------------------

    def _warmup(self) -> None:
        """
        Initialize EMA 10 for every active symbol.
        """

        symbols = (
            self._symbol_provider.get_symbols()
        )

        for symbol in symbols:
            self._warmup_symbol(symbol)

        pending_batches = self._pending_batches
        self._pending_batches = []

        for batch in pending_batches:
            self._process_candle_batch(batch)

    def _warmup_symbol(
        self,
        symbol: str,
    ) -> None:

        for attempt in range(1, self._max_warmup_retries + 1):
                try:
                    print(
                        f"IndicatorEngine: warming up {symbol} "
                        f"(attempt {attempt}/{self._max_warmup_retries})"
                    )

                    candles = self._historical_provider.get_historical_candles(
                        symbol=symbol,
                        timeframe=self._timeframe,
                        limit=self._warmup_limit,
                    )

                    if len(candles) < self._warmup_limit:
                        raise ValueError(
                            f"Not enough historical candles for {symbol}. "
                            f"Required={self._warmup_limit}, "
                            f"received={len(candles)}"
                        )

                    closes = [candle.close for candle in candles]

                    ema_10 = self._ema_calculator.calculate_from_closes(
                        closes
                    )

                    self._state_store.set(
                        SymbolIndicatorState(
                            symbol=symbol,
                            timeframe=self._timeframe,
                            ema_10=ema_10,
                            ready=True,
                        )
                    )

                    print(
                        f"IndicatorEngine: warm-up completed for {symbol}"
                    )

                    return

                except Exception as e:
                    print(
                        f"IndicatorEngine: warm-up failed for {symbol} "
                        f"(attempt {attempt}): {e}"
                    )

                    if attempt == self._max_warmup_retries:
                        raise

                    print(
                        f"IndicatorEngine: retrying {symbol} "
                        f"in {self._warmup_retry_delay} seconds"
                    )

                    time.sleep(self._warmup_retry_delay)

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

        for symbol in batch.candles:
            state = self._state_store.get(symbol, batch.timeframe)

            if state is None or not state.ready:
                self._pending_batches.append(batch)
                print(
                    f"IndicatorEngine: buffering candle batch "
                    f"because indicator state is not ready for {symbol}"
                )
                return

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