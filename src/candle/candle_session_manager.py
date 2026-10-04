from datetime import datetime

from event_system.event import Event
from event_system.event_bus import EventBus
from event_system.event_type import EventType

from candle.candle_scheduler import CandleScheduler


class CandleSessionManager:
    """
    Manage the candle system lifecycle.

    Responsibilities
    ----------------
    - Listen to market lifecycle events.
    - Finalize the final candle when the market closes.
    - Stop the candle scheduler after finalization.
    """

    def __init__(
        self,
        event_bus: EventBus,
        candle_scheduler: CandleScheduler,
    ) -> None:

        self._event_bus = event_bus
        self._candle_scheduler = candle_scheduler

    # ---------------------------------------------------------
    # Lifecycle
    # ---------------------------------------------------------

    def start(self) -> None:
        """
        Register market lifecycle event handlers.
        """

        self._event_bus.subscribe(
            EventType.MARKET_CLOSE,
            self._on_market_close,
        )

    # ---------------------------------------------------------
    # Event Handlers
    # ---------------------------------------------------------

    def _on_market_close(
        self,
        event: Event,
    ) -> None:
        """
        Finalize the final candle boundary and then
        stop the candle scheduler.
        """

        boundary: datetime = event.payload

        self._candle_scheduler.stop_after_boundary(
            boundary
        )

        self._event_bus.publish(
            Event(
                event_type=EventType.MARKET_PROCESSING_COMPLETE,
                payload=None,
            )
        )