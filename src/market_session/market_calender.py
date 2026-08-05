from datetime import date, timedelta
from .market_holidays import MARKET_HOLIDAYS

class MarketCalendar:
    """
    Determines whether a date is a trading day and
    calculates the next trading day.

    Version 1:
    - Monday to Friday are trading days.
    - Saturday and Sunday are non-trading days.
    - Holidays are supported.
    """

    def is_trading_day(self, current_date: date) -> bool:
        """
        Returns True if the given date is a trading day.
        """

        if current_date.weekday() >= 5:
            return False

        if current_date in MARKET_HOLIDAYS:
            return False

        return True

    def get_next_trading_day(self, current_date: date) -> date:
        """
        Returns the next available trading day.
        """

        if not isinstance(current_date, date):
            raise TypeError("current_date must be a datetime.date object")

        next_day = current_date + timedelta(days=1)

        while not self.is_trading_day(next_day):
            next_day += timedelta(days=1)

        return next_day