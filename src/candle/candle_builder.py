from datetime import datetime, timedelta

from event_system.event import Event
from event_system.event_bus import EventBus
from event_system.event_type import EventType

from market_data.models import Tick

from candle.candle_models import Candle, CandleBatch
from candle.candle_timeframe import CandleTimeframe


class CandleBuilder:
    """
    Builds time-based candles from incoming market ticks.

    Responsibilities:
        - Receive TICK_RECEIVED events.
        - Maintain currently forming candles.
        - Create a new candle when a new interval begins.
        - Update OHLC values for the current candle.
        - Finalize completed candle intervals.
        - Create CandleBatch objects from completed candles.
        - Publish completed CandleBatch events.

    The CandleBuilder does not decide when an interval ends.
    CandleScheduler is responsible for detecting the time boundary
    and calling finalize_interval().
    """

    def __init__(self, event_bus: EventBus) -> None:
        # ---------------------------------------------------------
        # Dependencies
        # ---------------------------------------------------------

        self._event_bus = event_bus

        # ---------------------------------------------------------
        # Runtime State
        # ---------------------------------------------------------

        # Stores only candles that are currently being formed.
        #
        # Key:
        #     (symbol, timeframe)
        #
        # Example:
        #     ("NIFTY", FIVE_MINUTES) -> Candle(10:15-10:20)
        #
        self._current_candles: dict[
            tuple[str, CandleTimeframe],
            Candle,
        ] = {}

    # =========================================================
    # Lifecycle
    # =========================================================

    def start(self) -> None:
        """
        Subscribe to market tick events.

        After start(), every TICK_RECEIVED event published
        through the EventBus will be received by _on_tick().
        """

        self._event_bus.subscribe(
            EventType.TICK_RECEIVED,
            self._on_tick,
        )

    # =========================================================
    # Interval Finalization API
    # =========================================================

    def finalize_interval(
        self,
        interval_start: datetime,
    ) -> None:
        """
        Finalize a completed candle interval.

        This method is called by CandleScheduler when a
        candle time boundary is reached.

        Example:

            Boundary = 10:20
            Completed interval = 10:15 - 10:20

        The completed candles are collected into a CandleBatch
        and published through the EventBus.
        """

        self._finalize_interval(interval_start)

    # =========================================================
    # Event Handler
    # =========================================================

    def _on_tick(self, event: Event) -> None:
        """
        Handle a TICK_RECEIVED event.

        The event payload contains one market Tick.
        """

        tick: Tick = event.payload

        self._process_tick(tick)

    # =========================================================
    # Tick Processing
    # =========================================================

    def _process_tick(self, tick: Tick) -> None:
        """
        Create or update the currently forming candle.

        Processing flow:

            Tick
              ↓
            Find 5-minute bucket
              ↓
            Check current candle
              ↓
            Create or update candle

        A tick does NOT publish a completed candle.

        Candle publication happens only when
        finalize_interval() is called by CandleScheduler.
        """

        timeframe = CandleTimeframe.FIVE_MINUTES

        key = (
            tick.symbol,
            timeframe,
        )

        # Determine which 5-minute interval this tick belongs to.
        start_time = self._get_bucket_start(
            tick.timestamp,
            timeframe,
        )

        end_time = (
            start_time + timedelta(minutes=5)
        )

        current_candle = self._current_candles.get(key)

        # ---------------------------------------------------------
        # Case 1: First tick for this symbol
        # ---------------------------------------------------------

        if current_candle is None:

            self._current_candles[key] = Candle(
                symbol=tick.symbol,
                timeframe=timeframe.value,
                start_time=start_time,
                end_time=end_time,
                open=tick.price,
                high=tick.price,
                low=tick.price,
                close=tick.price,
            )

            return

        # ---------------------------------------------------------
        # Case 2: Tick belongs to current interval
        # ---------------------------------------------------------

        if current_candle.start_time == start_time:

            self._update_candle(
                current_candle,
                tick.price,
            )

            return

        # ---------------------------------------------------------
        # Case 3: Tick belongs to a new interval
        # ---------------------------------------------------------

        # The previous candle is NOT published here.
        #
        # CandleScheduler is responsible for detecting the
        # completed time interval and calling finalize_interval().
        #
        # We simply start tracking the new interval.

        self._current_candles[key] = Candle(
            symbol=tick.symbol,
            timeframe=timeframe.value,
            start_time=start_time,
            end_time=end_time,
            open=tick.price,
            high=tick.price,
            low=tick.price,
            close=tick.price,
        )

    # =========================================================
    # Candle OHLC Update
    # =========================================================

    @staticmethod
    def _update_candle(
        candle: Candle,
        price: float,
    ) -> None:
        """
        Update the OHLC values of the currently forming candle.

        Open:
            Remains unchanged.

        High:
            Maximum price seen so far.

        Low:
            Minimum price seen so far.

        Close:
            Latest tick price.
        """

        candle.high = max(
            candle.high,
            price,
        )

        candle.low = min(
            candle.low,
            price,
        )

        candle.close = price

    # =========================================================
    # Completed Interval Finalization
    # =========================================================

    def _finalize_interval(
        self,
        interval_start: datetime,
    ) -> None:
        """
        Finalize all candles belonging to one completed interval.

        Example:

            interval_start = 10:15
            interval_end   = 10:20

        The method:

            1. Finds all completed candles for the interval.
            2. Collects them by symbol.
            3. Removes them from the currently forming state.
            4. Creates one CandleBatch.
            5. Publishes CANDLE_BATCH_CLOSED through EventBus.

        The completed candles are NOT lost.
        They are transferred from the active candle state
        into the CandleBatch payload.
        """

        timeframe = CandleTimeframe.FIVE_MINUTES

        interval_end = (
            interval_start + timedelta(minutes=5)
        )

        # Contains completed candles grouped by symbol.
        #
        # Example:
        #
        # {
        #     "NIFTY": Candle(...),
        #     "BANKNIFTY": Candle(...),
        # }
        #
        completed_candles: dict[str, Candle] = {}

        # Store keys that must be removed after collecting
        # the completed candles.
        keys_to_remove = []

        # ---------------------------------------------------------
        # Find completed candles
        # ---------------------------------------------------------

        for (
            key,
            candle,
        ) in self._current_candles.items():

            symbol, candle_timeframe = key

            # Ignore candles belonging to another timeframe.
            if candle_timeframe != timeframe:
                continue

            # Check whether this candle belongs to the
            # interval that has just completed.
            if (
                candle.start_time == interval_start
                and candle.end_time == interval_end
            ):

                completed_candles[symbol] = candle

                keys_to_remove.append(key)

        # ---------------------------------------------------------
        # Remove completed candles from active state
        # ---------------------------------------------------------

        # These candles are no longer "currently forming".
        #
        # They already exist inside completed_candles and will
        # shortly be transferred into CandleBatch.
        #
        for key in keys_to_remove:
            del self._current_candles[key]

        # ---------------------------------------------------------
        # Nothing completed
        # ---------------------------------------------------------

        if not completed_candles:
            return

        # ---------------------------------------------------------
        # Create CandleBatch
        # ---------------------------------------------------------

        batch = CandleBatch(
            timeframe=timeframe.value,
            start_time=interval_start,
            end_time=interval_end,
            candles=completed_candles,
        )

        # ---------------------------------------------------------
        # Publish completed candle batch
        # ---------------------------------------------------------

        self._event_bus.publish(
            Event(
                event_type=EventType.CANDLE_BATCH_CLOSED,
                payload=batch,
            )
        )

    # =========================================================
    # Time Bucket Calculation
    # =========================================================

    @staticmethod
    def _get_bucket_start(
        timestamp: datetime,
        timeframe: CandleTimeframe,
    ) -> datetime:
        """
        Determine the beginning of the candle interval
        to which a tick belongs.

        Example for 5-minute candles:

            10:15:32 → 10:15
            10:17:45 → 10:15
            10:19:59 → 10:15

            10:20:01 → 10:20
            10:23:12 → 10:20
        """

        if timeframe == CandleTimeframe.FIVE_MINUTES:

            minute = (
                timestamp.minute // 5
            ) * 5

            return timestamp.replace(
                minute=minute,
                second=0,
                microsecond=0,
            )

        raise ValueError(
            f"Unsupported timeframe: {timeframe}"
        )