from datetime import datetime

from event_system.event_bus import EventBus
from event_system.event_type import EventType

from market_session.market_state import MarketState
from market_session.market_session_manager import MarketSessionManager
from market_session.models import NextMarketEvent


# =========================================================
# Fake Schedulers
# =========================================================

class FakeOpenScheduler:

    def get_next_event(self, current_datetime: datetime):

        return NextMarketEvent(
            event=EventType.MARKET_CLOSE,
            event_time=current_datetime,
            sleep_seconds=0,
            market_state=MarketState.OPEN
        )

class FakeCloseScheduler:

    def get_next_event(self, current_datetime: datetime):

        return NextMarketEvent(
            event=EventType.MARKET_CLOSE,
            event_time=current_datetime,
            sleep_seconds=0,
            market_state=MarketState.OPEN
        )


# =========================================================
# Test: MARKET_OPEN event is published
# =========================================================

def test_process_one_iteration_market_open():

    # Arrange
    scheduler = FakeOpenScheduler()
    event_bus = EventBus()

    received_events = []

    def callback(event):
        received_events.append(event)

    event_bus.subscribe(
        EventType.MARKET_OPEN,
        callback
    )

    manager = MarketSessionManager(
        scheduler=scheduler,
        event_bus=event_bus
    )

    # Act
    manager._process_one_iteration()

    # Assert
    assert manager.market_state == MarketState.OPEN
    assert len(received_events) == 1
    assert received_events[0].event_type == EventType.MARKET_OPEN


# =========================================================
# Test: MARKET_CLOSE event is published
# =========================================================

def test_process_one_iteration_market_close():

    # Arrange
    scheduler = FakeCloseScheduler()
    event_bus = EventBus()

    received_events = []

    def callback(event):
        received_events.append(event)

    event_bus.subscribe(
        EventType.MARKET_CLOSE,
        callback
    )

    manager = MarketSessionManager(
        scheduler=scheduler,
        event_bus=event_bus
    )

    # Act
    manager._process_one_iteration()

    # Assert
    assert manager.market_state == MarketState.OPEN
    assert len(received_events) == 1
    assert received_events[0].event_type == EventType.MARKET_CLOSE


# =========================================================
# Test: wait() returns True after timeout
# =========================================================

def test_wait_timeout():

    manager = MarketSessionManager(
        scheduler=FakeOpenScheduler(),
        event_bus=EventBus()
    )

    assert manager._wait(0) is True


# =========================================================
# Test: wait() is interrupted by stop event
# =========================================================

def test_wait_interrupted():

    manager = MarketSessionManager(
        scheduler=FakeOpenScheduler(),
        event_bus=EventBus()
    )

    manager._stop_event.set()

    assert manager._wait(10) is False


# =========================================================
# Test: start() creates background thread
# =========================================================

def test_start():

    manager = MarketSessionManager(
        scheduler=FakeOpenScheduler(),
        event_bus=EventBus()
    )

    manager.start()

    assert manager._running is True
    assert manager._thread is not None

    manager.stop()


# =========================================================
# Test: stop() stops background thread
# =========================================================

def test_stop():

    manager = MarketSessionManager(
        scheduler=FakeOpenScheduler(),
        event_bus=EventBus()
    )

    manager.start()
    manager.stop()

    assert manager._running is False