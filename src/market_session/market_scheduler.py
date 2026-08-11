from datetime import datetime

from event_system.event_type import EventType

from market_session.market_state import MarketState
from market_session.market_calendar import MarketCalendar
from market_session.market_config import MarketConfig
from market_session.models import NextMarketEvent


class MarketScheduler:
    """
    Determine the next market lifecycle event.

    Responsibilities
    ----------------
    - Understand trading-day rules through MarketCalendar.
    - Understand market timings through MarketConfig.
    - Return the next market event along with:
        * event type
        * event timestamp
        * sleep duration
        * current market state

    The scheduler is the single source of truth for market timing.
    """

    def __init__(
        self,
        calendar: MarketCalendar,
        config: MarketConfig = MarketConfig()
    ) -> None:

        self._calendar = calendar
        self._config = config

    # ---------------------------------------------------------
    # Time state helpers
    # ---------------------------------------------------------

    def _is_before_market_open(
        self,
        current_datetime: datetime
    ) -> bool:
        """
        Return True if current time is before market open.
        """

        return (
            current_datetime.time() < self._config.MARKET_OPEN
        )

    def _is_during_market_hours(
        self,
        current_datetime: datetime
    ) -> bool:
        """
        Return True if market is currently open.
        """

        current_time = current_datetime.time()

        return (
            self._config.MARKET_OPEN
            <= current_time
            < self._config.MARKET_CLOSE
        )

    # ---------------------------------------------------------
    # Event builders
    # ---------------------------------------------------------

    def _today_market_open(
        self,
        current_datetime: datetime
    ) -> NextMarketEvent:
        """
        Build today's MARKET_OPEN event.
        """

        event_time = datetime.combine(
            current_datetime.date(),
            self._config.MARKET_OPEN,
            tzinfo=current_datetime.tzinfo
        )

        return self._build_market_open_event(
            event_time,
            current_datetime
        )

    def _today_market_close(
        self,
        current_datetime: datetime
    ) -> NextMarketEvent:
        """
        Build today's MARKET_CLOSE event.
        Used when market is already open.
        """

        event_time = datetime.combine(
            current_datetime.date(),
            self._config.MARKET_CLOSE,
            tzinfo=current_datetime.tzinfo
        )

        return self._build_market_close_event(
            event_time,
            current_datetime
        )

    def _next_trading_day_open(
        self,
        current_datetime: datetime
    ) -> NextMarketEvent:
        """
        Build MARKET_OPEN event for the next trading day.
        Used after market close or on holidays/weekends.
        """

        next_day = self._calendar.get_next_trading_day(
            current_datetime.date()
        )

        event_time = datetime.combine(
            next_day,
            self._config.MARKET_OPEN,
            tzinfo=current_datetime.tzinfo
        )

        return self._build_market_open_event(
            event_time,
            current_datetime
        )

    # ---------------------------------------------------------
    # Low-level model builders
    # ---------------------------------------------------------

    def _build_market_open_event(
        self,
        event_time: datetime,
        current_datetime: datetime
    ) -> NextMarketEvent:
        """
        Create a MARKET_OPEN event model.
        Current market state before open is CLOSED.
        """

        sleep_seconds = self._calculate_sleep_seconds(
            current_datetime,
            event_time
        )

        return NextMarketEvent(
            event=EventType.MARKET_OPEN,
            event_time=event_time,
            sleep_seconds=sleep_seconds,
            market_state=MarketState.CLOSED
        )

    def _build_market_close_event(
        self,
        event_time: datetime,
        current_datetime: datetime
    ) -> NextMarketEvent:
        """
        Create a MARKET_CLOSE event model.
        Current market state during trading hours is OPEN.
        """

        sleep_seconds = self._calculate_sleep_seconds(
            current_datetime,
            event_time
        )

        return NextMarketEvent(
            event=EventType.MARKET_CLOSE,
            event_time=event_time,
            sleep_seconds=sleep_seconds,
            market_state=MarketState.OPEN
        )

    # ---------------------------------------------------------
    # Utility
    # ---------------------------------------------------------

    def _calculate_sleep_seconds(
        self,
        current_datetime: datetime,
        event_time: datetime
    ) -> int:
        """
        Calculate seconds until the target event.
        """

        return int(
            (event_time - current_datetime).total_seconds()
        )

    # ---------------------------------------------------------
    # Public API
    # ---------------------------------------------------------

    def get_next_event(
        self,
        current_datetime: datetime
    ) -> NextMarketEvent:
        """
        Return the next market lifecycle event.

        Cases
        -----
        1. Holiday / weekend:
            - next trading day MARKET_OPEN
            - state CLOSED

        2. Before market open:
            - today's MARKET_OPEN
            - state CLOSED

        3. During market hours:
            - today's MARKET_CLOSE
            - state OPEN

        4. After market close:
            - next trading day MARKET_OPEN
            - state CLOSED
        """

        # Case 1: Holiday or weekend.
        if not self._calendar.is_trading_day(
            current_datetime.date()
        ):
            return self._next_trading_day_open(
                current_datetime
            )

        # Case 2: Before market open.
        if self._is_before_market_open(
            current_datetime
        ):
            return self._today_market_open(
                current_datetime
            )

        # Case 3: Market currently open.
        if self._is_during_market_hours(
            current_datetime
        ):
            return self._today_market_close(
                current_datetime
            )

        # Case 4: After market close.
        return self._next_trading_day_open(
            current_datetime
        )