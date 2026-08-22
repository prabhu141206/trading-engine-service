from datetime import datetime, timedelta
from typing import Callable

from candle.candle_timeframe import CandleTimeframe

import threading
from datetime import datetime, timedelta
from typing import Callable


class CandleScheduler:
    """
    Determines candle boundaries and notifies a callback
    when a candle interval is completed.
    """

    def __init__(
        self,
        timeframe: CandleTimeframe,
        on_boundary: Callable[[datetime], None],
    ) -> None:

        self._timeframe = timeframe
        self._on_boundary = on_boundary

        self._running = False
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    # ---------------------------------------------------------
    # Boundary Calculation
    # ---------------------------------------------------------

    def get_next_boundary(
        self,
        current_time: datetime,
    ) -> datetime:

        if self._timeframe == CandleTimeframe.FIVE_MINUTES:

            minute = (
                (current_time.minute // 5) + 1
            ) * 5

            if minute >= 60:
                return (
                    current_time.replace(
                        minute=0,
                        second=0,
                        microsecond=0,
                    )
                    + timedelta(hours=1)
                )

            return current_time.replace(
                minute=minute,
                second=0,
                microsecond=0,
            )

        raise ValueError(
            f"Unsupported timeframe: {self._timeframe}"
        )

    # ---------------------------------------------------------
    # Interval Start
    # ---------------------------------------------------------

    def get_interval_start(
        self,
        boundary: datetime,
    ) -> datetime:

        if self._timeframe == CandleTimeframe.FIVE_MINUTES:
            return boundary - timedelta(minutes=5)

        raise ValueError(
            f"Unsupported timeframe: {self._timeframe}"
        )

    # ---------------------------------------------------------
    # Boundary Notification
    # ---------------------------------------------------------

    def trigger_boundary(
        self,
        boundary: datetime,
    ) -> None:
        """
        Notify the consumer that the interval ending at
        `boundary` has completed.
        """

        interval_start = self.get_interval_start(
            boundary
        )

        # Callback to notify that the candle interval has completed
        # This will call to finialize candle method inside candle builder
        self._on_boundary(interval_start)


    # ---------------------------------------------------------
    # Deterministic Cycle
    # ---------------------------------------------------------

    def run_once(self, current_time: datetime) -> None:
        """
        Process one candle scheduling cycle.

        Calculates the next candle boundary and triggers
        the boundary callback for the completed interval.
        """

        boundary = self.get_next_boundary(current_time)

        self.trigger_boundary(boundary)


    # ---------------------------------------------------------
    # Runtime Lifecycle
    # ---------------------------------------------------------

    def start(self) -> None:
        """
        Start the scheduler background thread.
        """

        if self._running:
            return

        self._running = True
        self._stop_event.clear()

        self._thread = threading.Thread(
            target=self._run,
            daemon=True,
        )

        self._thread.start()


    def stop(self) -> None:
        """
        Stop the scheduler background thread.
        """

        if not self._running:
            return

        self._running = False
        self._stop_event.set()

        if self._thread is not None:
            self._thread.join()

        self._thread = None

    # ---------------------------------------------------------
    # Internal Runtime Loop
    # --------------------------------------------------------

    def _run(self) -> None:
        """
        Continuously wait for candle boundaries and trigger them.
        """

        while self._running:

            current_time = datetime.now()

            boundary = self.get_next_boundary(
                current_time
            )

            wait_seconds = (
                boundary - current_time
            ).total_seconds()

            interrupted = self._stop_event.wait(
                timeout=wait_seconds
            )

            if interrupted:
                break

            self.trigger_boundary(boundary)