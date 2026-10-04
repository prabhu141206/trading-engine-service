from datetime import datetime
from unittest.mock import Mock

from candle.candle_session_manager import CandleSessionManager
from event_system.event import Event
from event_system.event_bus import EventBus
from event_system.event_type import EventType


def test_market_close_reaches_candle_session_manager():
    """
    Verify the candle shutdown path through EventBus.

    Test flow:

        MARKET_CLOSE
            ↓
        EventBus
            ↓
        CandleSessionManager
            ↓
        CandleScheduler.stop_after_boundary()

    The real scheduler thread is not started here.
    The purpose of this test is only to verify event wiring.
    """

    # ---------------------------------------------------------
    # Arrange
    # ---------------------------------------------------------

    event_bus = EventBus()

    # Mock the scheduler because this test is checking
    # EventBus-to-CandleSessionManager communication.
    candle_scheduler = Mock()

    candle_session_manager = CandleSessionManager(
        event_bus=event_bus,
        candle_scheduler=candle_scheduler,
    )

    # Register the candle lifecycle handler.
    candle_session_manager.start()

    # The final candle is 14:55 → 15:00.
    final_boundary = datetime(
        2026,
        9,
        27,
        15,
        0,
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

    # MARKET_CLOSE must reach CandleSessionManager,
    # which must forward the final boundary to the scheduler.
    candle_scheduler.stop_after_boundary.assert_called_once_with(
        final_boundary
    )