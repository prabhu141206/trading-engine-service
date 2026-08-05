from datetime import datetime

from market_session.market_calendar import MarketCalendar
from market_session.market_scheduler import MarketScheduler
from market_session.market_event import MarketEvent


calendar = MarketCalendar()
scheduler = MarketScheduler(calendar)



#Test 1 - Before Market Open
def test_before_market_open():

    #08:30
    current = datetime(2026, 8, 5, 8, 30)

    event = scheduler.get_next_event(current)

    assert event.event == MarketEvent.MARKET_OPEN
    assert event.event_time == datetime(2026, 8, 5, 9, 15)
    assert event.sleep_seconds == 45 * 60


#Test 2 - During Market Hours
def test_during_market_hours():

    current = datetime(2026, 8, 5, 11, 0)

    event = scheduler.get_next_event(current)

    assert event.event == MarketEvent.MARKET_OPEN
    assert event.event_time == datetime(2026, 8, 6, 9, 15)

#Test 3 - After Market Close
def test_after_market_close():

    current = datetime(2026, 8, 5, 17, 0)

    event = scheduler.get_next_event(current)

    assert event.event == MarketEvent.MARKET_OPEN
    assert event.event_time == datetime(2026, 8, 6, 9, 15)


#Test 4 - Saturday
def test_weekend():

    current = datetime(2026, 8, 8, 10, 0)

    event = scheduler.get_next_event(current)

    assert event.event == MarketEvent.MARKET_OPEN
    assert event.event_time == datetime(2026, 8, 10, 9, 15)

#Test 5 - Holiday
def test_holiday():

    current = datetime(2026, 1, 26, 10, 0)

    event = scheduler.get_next_event(current)

    assert event.event == MarketEvent.MARKET_OPEN
    assert event.event_time == datetime(2026, 1, 27, 9, 15)

# Test 6 - Friday After Market
# This checks weekend skipping.
def test_friday_after_market():

    current = datetime(2026, 8, 7, 18, 0)

    event = scheduler.get_next_event(current)

    assert event.event_time == datetime(2026, 8, 10, 9, 15)

#Test 7 - Monday Before Market
def test_monday_before_market():

    current = datetime(2026, 8, 3, 9, 0)

    event = scheduler.get_next_event(current)

    assert event.event_time == datetime(2026, 8, 3, 9, 15)

#Test 8 - get sleep_seconds_before_market_open
def test_sleep_seconds_before_market_open():

    current = datetime(2026, 8, 5, 9, 0)

    event = scheduler.get_next_event(current)

    assert event.sleep_seconds == 15 * 60