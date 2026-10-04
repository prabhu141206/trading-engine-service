from datetime import datetime
from unittest.mock import Mock

from candle.candle_session_manager import CandleSessionManager
from event_system.event import Event
from event_system.event_bus import EventBus
from event_system.event_type import EventType


def test_market_close_finalizes_last_candle_boundary():
    """
    Verify that CandleSessionManager responds to MARKET_CLOSE
    by asking CandleScheduler to process the final candle boundary.

    Test flow:

        MARKET_CLOSE event
                ↓
        CandleSessionManager
                ↓
        CandleScheduler.stop_after_boundary()
                ↓
        Final candle boundary is processed

    This test does NOT test CandleScheduler itself.
    It only verifies that CandleSessionManager correctly
    coordinates the market-close event with the scheduler.
    """

    # ---------------------------------------------------------
    # Arrange
    # ---------------------------------------------------------

    # Create the shared event bus used by the lifecycle manager.
    event_bus = EventBus()

    # Create a mock scheduler.
    #
    # We don't want to run a real scheduler thread in this test.
    # We only want to verify that the correct method is called
    # with the correct boundary.
    candle_scheduler = Mock()

    # Create the component under test.
    candle_session_manager = CandleSessionManager(
        event_bus=event_bus,
        candle_scheduler=candle_scheduler,
    )

    # Register MARKET_CLOSE event handling.
    candle_session_manager.start()

    # The final candle is:
    #
    #     14:55 → 15:00
    #
    # Therefore the final boundary is 15:00.
    final_boundary = datetime(
        2026,
        9,
        27,
        15,
        0,
    )

    market_close_event = Event(
        event_type=EventType.MARKET_CLOSE,
        payload=final_boundary,
    )

    # ---------------------------------------------------------
    # Act
    # ---------------------------------------------------------

    # Publish MARKET_CLOSE.
    #
    # EventBus should call CandleSessionManager._on_market_close().
    event_bus.publish(market_close_event)

    # ---------------------------------------------------------
    # Assert
    # ---------------------------------------------------------

    # Verify that the candle scheduler was instructed
    # to process the final boundary.
    candle_scheduler.stop_after_boundary.assert_called_once_with(
        final_boundary
    )


def test_market_close_publishes_processing_complete():
    """
    Verify that CandleSessionManager publishes
    MARKET_PROCESSING_COMPLETE after the final candle
    boundary has been requested.

    Test flow:

        MARKET_CLOSE
                ↓
        CandleSessionManager
                ↓
        stop_after_boundary()
                ↓
        MARKET_PROCESSING_COMPLETE
    """

    # ---------------------------------------------------------
    # Arrange
    # ---------------------------------------------------------

    event_bus = EventBus()

    candle_scheduler = Mock()

    candle_session_manager = CandleSessionManager(
        event_bus=event_bus,
        candle_scheduler=candle_scheduler,
    )

    candle_session_manager.start()

    # Store events received by the test subscriber.
    received_events = []

    def handler(event):
        """Store lifecycle events published by CandleSessionManager."""
        received_events.append(event)

    event_bus.subscribe(
        EventType.MARKET_PROCESSING_COMPLETE,
        handler,
    )

    final_boundary = datetime(
        2026,
        9,
        27,
        15,
        0,
    )

    market_close_event = Event(
        event_type=EventType.MARKET_CLOSE,
        payload=final_boundary,
    )

    # ---------------------------------------------------------
    # Act
    # ---------------------------------------------------------

    event_bus.publish(market_close_event)

    # ---------------------------------------------------------
    # Assert
    # ---------------------------------------------------------

    # Final candle boundary must be requested first.
    candle_scheduler.stop_after_boundary.assert_called_once_with(
        final_boundary
    )

    # MARKET_PROCESSING_COMPLETE must be published.
    assert len(received_events) == 1

    assert (
        received_events[0].event_type
        == EventType.MARKET_PROCESSING_COMPLETE
    )