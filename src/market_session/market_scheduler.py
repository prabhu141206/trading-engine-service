from datetime import datetime

from event_system.event_type import EventType

from .market_calendar import MarketCalendar
from .market_config import MarketConfig
from .models import NextMarketEvent


class MarketScheduler:

    def __init__(
        self,
        calendar: MarketCalendar,
        config: MarketConfig = MarketConfig()
    ):
        self._calendar = calendar
        self._config = config


    def _is_before_market_open(self,current_datetime: datetime) -> bool:
        return current_datetime.time() < self._config.MARKET_OPEN

    def _today_market_open(self,current_datetime: datetime) -> NextMarketEvent:

        event_time = datetime.combine(
            current_datetime.date(),
            self._config.MARKET_OPEN
        )

        return self._build_market_open_event(
            event_time,
            current_datetime
        )

    def _next_trading_day_open(self,current_datetime: datetime) -> NextMarketEvent:

        next_day = self._calendar.get_next_trading_day(
            current_datetime.date()
        )

        event_time = datetime.combine(
            next_day,
            self._config.MARKET_OPEN
        )

        return self._build_market_open_event(
            event_time,
            current_datetime
        )

    def _build_market_open_event(self,event_time: datetime,current_datetime: datetime) -> NextMarketEvent:

        sleep_seconds = self._calculate_sleep_seconds(
            current_datetime,
            event_time
        )

        return NextMarketEvent(
            event=EventType.MARKET_OPEN,
            event_time=event_time,
            sleep_seconds=sleep_seconds
        )

    def _calculate_sleep_seconds(self,current_datetime: datetime,event_time: datetime) -> int:

        return int(
            (event_time - current_datetime).total_seconds()
        )

    def get_next_event(self, current_datetime: datetime) -> NextMarketEvent:

        if not self._calendar.is_trading_day(current_datetime.date()):
            return self._next_trading_day_open(current_datetime)

        if self._is_before_market_open(current_datetime):
            return self._today_market_open(current_datetime)

        return self._next_trading_day_open(current_datetime)

    