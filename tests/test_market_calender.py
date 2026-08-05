from datetime import date

from src.market_session.market_calender import MarketCalendar


calendar = MarketCalendar()


# ---------- Trading Days ----------

def test_monday_is_trading_day():
    assert calendar.is_trading_day(date(2026, 8, 3)) is True


def test_friday_is_trading_day():
    assert calendar.is_trading_day(date(2026, 8, 7)) is True


# ---------- Weekends ----------

def test_saturday_is_not_trading_day():
    assert calendar.is_trading_day(date(2026, 8, 8)) is False


def test_sunday_is_not_trading_day():
    assert calendar.is_trading_day(date(2026, 8, 9)) is False


# ---------- Holidays ----------

def test_republic_day_is_not_trading_day():
    assert calendar.is_trading_day(date(2026, 1, 26)) is False


def test_christmas_is_not_trading_day():
    assert calendar.is_trading_day(date(2026, 12, 25)) is False


# ---------- Next Trading Day ----------

def test_next_trading_day_after_wednesday():
    assert calendar.get_next_trading_day(
        date(2026, 8, 5)
    ) == date(2026, 8, 6)


def test_next_trading_day_after_friday():
    assert calendar.get_next_trading_day(
        date(2026, 8, 7)
    ) == date(2026, 8, 10)


def test_next_trading_day_after_holiday():
    # Republic Day (Monday) -> Tuesday
    assert calendar.get_next_trading_day(
        date(2026, 1, 26)
    ) == date(2026, 1, 27)


def test_next_trading_day_skips_weekend_and_holiday():
    # Friday -> Saturday -> Sunday -> Monday(Holiday) -> Tuesday
    assert calendar.get_next_trading_day(
        date(2026, 1, 23)
    ) == date(2026, 1, 27)