from datetime import datetime
from threading import Event, Thread

from event_system.event import Event as SystemEvent
from event_system.event_bus import EventBus

from market_session.market_config import IST
from market_session.market_scheduler import MarketScheduler
from market_session.market_state import MarketState
from market_session.models import NextMarketEvent


class MarketSessionManager:
    """
    Controls the lifecycle of the market session.

    Responsibilities:
        - Ask MarketScheduler for the next market event.
        - Update the current market state.
        - Wait until the event time.
        - Publish the event through EventBus.
        - Repeat until stopped.
    """

    def __init__(
        self,
        scheduler: MarketScheduler,
        event_bus: EventBus
    ) -> None:

        self._scheduler = scheduler
        self._event_bus = event_bus

        self._running = False
        self._thread: Thread | None = None

        # Used for interruptible waiting
        self._stop_event = Event()

        # Current market state
        self._current_market_state = MarketState.WAITING

    # ---------------------------------------------------------
    # Public API
    # ---------------------------------------------------------

    def start(self) -> None:

        if self._running:
            return

        self._running = True
        self._stop_event.clear()

        self._thread = Thread(
            target=self._run,
            name="MarketSessionManager",
            daemon=True
        )

        self._thread.start()

    def stop(self) -> None:

        if not self._running:
            return

        self._running = False

        # Interrupt waiting immediately
        self._stop_event.set()

        if self._thread is not None:
            self._thread.join()

    # ---------------------------------------------------------
    # Private Methods
    # ---------------------------------------------------------

    def _run(self) -> None:

        while self._running:

            if not self._process_one_iteration():
                break

    def _process_one_iteration(self) -> bool:
        """
        Execute one scheduling cycle.

        This method is separated from _run() to simplify unit testing.
        """

        next_event = self._scheduler.get_next_event(
            datetime.now(IST)
        )

        # Scheduler decides the current market state
        self._current_market_state = next_event.market_state

        # Number of seconds to wait
        if not self._wait(next_event.sleep_seconds):
            return False

        self._publish(next_event)

        return True

    def _wait(self, seconds: int) -> bool:
        """
        Wait until timeout expires or stop() is called.

        Returns:
            True  -> timeout completed normally.
            False -> stop requested.
        """

        interrupted = self._stop_event.wait(timeout=seconds)

        return not interrupted

    def _publish(
        self,
        next_event: NextMarketEvent
    ) -> None:
        """
        Publish the scheduled market event.

        NOTE:
        MarketSessionManager DOES NOT modify market state here.
        MarketScheduler is the single source of truth for MarketState.
        """

        event = SystemEvent(
            event_type=next_event.event,
            payload=next_event
        )

        self._event_bus.publish(event)

    # ---------------------------------------------------------
    # Properties
    # ---------------------------------------------------------

    @property
    def market_state(self) -> MarketState:
        return self._current_market_state