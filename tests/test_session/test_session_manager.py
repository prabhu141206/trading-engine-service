from event_system.event import Event
from event_system.event_bus import EventBus
from event_system.event_type import EventType
from src.session.session_manager import SessionManager


def test_subscribe_market_open():

    # Arrange
    event_bus = EventBus()

    manager = SessionManager(
        event_bus=event_bus
    )

    # Act
    manager.start()

    # Assert
    assert len(
        event_bus._subscribers[EventType.MARKET_OPEN]
    ) == 1




def test_subscribe_market_close():

    # Arrange
    event_bus = EventBus()

    manager = SessionManager(
        event_bus=event_bus
    )

    # Act
    manager.start()

    # Assert
    assert len(
        event_bus._subscribers[EventType.MARKET_CLOSE]
    ) == 1


def test_create_user_sessions_on_market_open():

    # Arrange
    event_bus = EventBus()

    manager = SessionManager(
        event_bus=event_bus
    )

    manager.start()

    event = Event(
        event_type=EventType.MARKET_OPEN,
        payload=None
    )

    # Act
    event_bus.publish(event)

    # Assert
    assert len(manager._sessions) == 3

    assert 101 in manager._sessions
    assert 202 in manager._sessions
    assert 303 in manager._sessions


def test_remove_user_sessions_on_market_close():

    event_bus = EventBus()

    manager = SessionManager(event_bus)
    manager.start()

    # Open market first
    event_bus.publish(Event(EventType.MARKET_OPEN, None))

    assert len(manager._sessions) == 3

    # Close market
    event_bus.publish(Event(EventType.MARKET_CLOSE, None))

    assert len(manager._sessions) == 0