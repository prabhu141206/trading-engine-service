from datetime import datetime
from unittest.mock import Mock

from event_system.event import Event
from event_system.event_bus import EventBus
from event_system.event_type import EventType

from candle.candle_session_manager import CandleSessionManager
from session.session_manager import SessionManager


def test_market_shutdown_flow():

    # ---------------------------------------------------------
    # Arrange
    # ---------------------------------------------------------

    event_bus = EventBus()

    candle_scheduler = Mock()

    session_manager = SessionManager(
        event_bus=event_bus,
        subscription_registry=Mock(),
        strategy_registry=Mock(),
        strategy_user_registry=Mock(),
        user_session_repository=Mock(),
    )

    candle_session_manager = CandleSessionManager(
        event_bus=event_bus,
        candle_scheduler=candle_scheduler,
    )

    candle_session_manager.start()
    session_manager.start()
    
    # Store MARKET_PROCESSING_COMPLETE events.
    processing_complete_events = []

    def on_processing_complete(event):
        processing_complete_events.append(event)

    event_bus.subscribe(
        EventType.MARKET_PROCESSING_COMPLETE,
        on_processing_complete,
    )



    final_boundary = datetime(
        2026, 9, 27, 15, 0
    )

    # ---------------------------------------------------------
    # Act
    # ---------------------------------------------------------

    event_bus.publish(
        Event(
            event_type=EventType.MARKET_CLOSE,
            payload=final_boundary,
        )
    )

    # ---------------------------------------------------------
    # Assert
    # ---------------------------------------------------------

    candle_scheduler.stop_after_boundary.assert_called_once_with(
        final_boundary
    )


    # CandleSessionManager must publish the completion event
    # after requesting the final candle boundary.
    assert len(processing_complete_events) == 1

    assert (
        processing_complete_events[0].event_type
        == EventType.MARKET_PROCESSING_COMPLETE
    )