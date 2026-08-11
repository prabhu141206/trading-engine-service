from datetime import datetime
from threading import Event, Thread

from event_system.event import Event as SystemEvent
from event_system.event_type import EventType
from event_system.event_bus import EventBus

from market_session.market_config import IST
from market_session.market_scheduler import MarketScheduler
from market_session.market_state import MarketState
from market_session.models import NextMarketEvent


class MarketSessionManager:
    """
    Control the market session lifecycle.

    Responsibilities
    ----------------
    - Ask MarketScheduler for the next market event.
    - Update the current market state.
    - Wait until the scheduled event time.
    - Publish the market event through EventBus.
    - Repeat until stop() is called.

    Important
    ---------
    Waiting is an internal behavior of this manager, not a market state.
    The market can only be OPEN or CLOSED.
    """

    def __init__(
        self,
        scheduler: MarketScheduler,
        event_bus: EventBus
    ) -> None:
        """
        Initialize MarketSessionManager.

        Parameters
        ----------
        scheduler:
            Component responsible for market calendar and timing logic.

        event_bus:
            Shared event bus used to publish market lifecycle events.
        """

        self._scheduler = scheduler
        self._event_bus = event_bus

        self._running = False
        self._thread: Thread | None = None

        # Used to interrupt waiting immediately when stop() is called.
        self._stop_event = Event()

        # Initial market state before the first scheduler evaluation.
        self._current_market_state = MarketState.CLOSED

        # Prevent duplicate startup MARKET_OPEN publication.
        self._startup_bootstrap_done = False

    # ---------------------------------------------------------
    # Public API
    # ---------------------------------------------------------

    def start(self) -> None:
        """
        Start the market session loop in a background thread.

        Calling start() multiple times has no effect.
        """

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
        """
        Stop the market session loop gracefully.

        If the manager is currently waiting, the wait is interrupted
        immediately and the background thread exits.
        """

        if not self._running:
            return

        self._running = False

        # Interrupt any active wait.
        self._stop_event.set()

        if self._thread is not None:
            self._thread.join()

    # ---------------------------------------------------------
    # Internal loop
    # ---------------------------------------------------------

    def _run(self) -> None:
        """
        Continuously process market scheduling cycles.
        """

        while self._running:

            if not self._process_one_iteration():
                break

    def _process_one_iteration(self) -> bool:
        """
        Execute one scheduler cycle.
        """

        '''
        dataformat of get_next_event() is as follows:

                NextMarketEvent(
                    event=EventType.MARKET_CLOSE,
                    event_time=2026-08-11 15:30,
                    sleep_seconds=16200,
                    market_state=MarketState.OPEN
                )

                Current state : OPEN
                Next action   : MARKET_CLOSE
                Action time   : 15:30
                Wait duration : 16200 sec
        '''

        next_event = self._scheduler.get_next_event(
            datetime.now(IST)
        )

        # Scheduler is the single source of truth for market state.
        self._current_market_state = next_event.market_state

        # Handle application startup during market hours.
        self._bootstrap_if_market_already_open(next_event)

        # Wait until the scheduled event time.
        if not self._wait(next_event.sleep_seconds):
            return False

        self._publish(next_event)

        return True

    def _wait(self, seconds: int) -> bool:
        """
        Wait until timeout expires or stop() is called.

        This method represents the manager's waiting behavior.
        It does not change the market state.

        Parameters
        ----------
        seconds:
            Number of seconds to wait.

        Returns
        -------
        True
            Timeout completed normally.

        False
            Waiting was interrupted by stop().
        """

        interrupted = self._stop_event.wait(timeout=seconds)

        return not interrupted


    def _bootstrap_if_market_already_open(
        self,
        next_event: NextMarketEvent
    ) -> None:
        """
        Publish MARKET_OPEN immediately when the application starts
        during market hours.

        This allows SessionManager and other subscribers to build
        runtime state without waiting for the next trading day.
        """

        if self._startup_bootstrap_done:
            return

        if next_event.market_state != MarketState.OPEN:
            self._startup_bootstrap_done = True
            return

        bootstrap_event = SystemEvent(
            event_type=EventType.MARKET_OPEN
        )

        self._event_bus.publish(bootstrap_event)

        self._startup_bootstrap_done = True


    # ---------------------------------------------------------
    # Event publishing
    # ---------------------------------------------------------

    def _publish(
        self,
        next_event: NextMarketEvent
    ) -> None:
        """
        Publish the scheduled market lifecycle event.

        Examples
        --------
        - MARKET_OPEN
        - MARKET_CLOSE

        Subscribers receive the event through EventBus.
        """

        event = SystemEvent(
            event_type=next_event.event
        )

        self._event_bus.publish(event)

    # ---------------------------------------------------------
    # Read-only state
    # ---------------------------------------------------------

    @property
    def market_state(self) -> MarketState:
        """
        Return the current market state.

        Returns
        -------
        MarketState
            OPEN or CLOSED.
        """

        return self._current_market_state