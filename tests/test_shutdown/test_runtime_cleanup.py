from unittest.mock import Mock

from event_system.event import Event
from event_system.event_bus import EventBus
from event_system.event_type import EventType

from session.session_manager import SessionManager
from indicators.indicator_engine import IndicatorEngine
from strategy.strategy_engine import StrategyEngine


def test_market_processing_complete_cleans_runtime():

    # ---------------------------------------------------------
    # Arrange
    # ---------------------------------------------------------

    event_bus = EventBus()

    session_manager = Mock(spec=SessionManager)
    indicator_engine = Mock(spec=IndicatorEngine)
    strategy_engine = Mock(spec=StrategyEngine)

    event_bus.subscribe(
        EventType.MARKET_PROCESSING_COMPLETE,
        lambda event: session_manager.shutdown_runtime(),
    )

    event_bus.subscribe(
        EventType.MARKET_PROCESSING_COMPLETE,
        lambda event: indicator_engine.shutdown_runtime(),
    )

    event_bus.subscribe(
        EventType.MARKET_PROCESSING_COMPLETE,
        lambda event: strategy_engine.shutdown_runtime(),
    )

    # ---------------------------------------------------------
    # Act
    # ---------------------------------------------------------

    event_bus.publish(
        Event(
            event_type=EventType.MARKET_PROCESSING_COMPLETE,
        )
    )

    # ---------------------------------------------------------
    # Assert
    # ---------------------------------------------------------

    session_manager.shutdown_runtime.assert_called_once()
    indicator_engine.shutdown_runtime.assert_called_once()
    strategy_engine.shutdown_runtime.assert_called_once()
    