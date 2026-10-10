
import logging
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from typing import Deque
from collections import deque

from .event import Event
from .event_type import EventType


logger = logging.getLogger(__name__)

MAX_RECORDED_FAILURES = 100


@dataclass
class SubscriberFailure:
    event: Event
    callback: Callable[[Event], None]
    exception: Exception


class EventBus:

    def __init__(self):
        self._subscribers = defaultdict(list)
        self.failures: Deque[SubscriberFailure] = deque(
            maxlen=MAX_RECORDED_FAILURES
        )

    def subscribe(
        self,
        event_type: EventType,
        callback: Callable[[Event], None],
    ) -> None:
        if callback not in self._subscribers[event_type]:
            self._subscribers[event_type].append(callback)

    def unsubscribe(
        self,
        event_type: EventType,
        callback: Callable[[Event], None],
    ) -> None:
        if callback in self._subscribers[event_type]:
            self._subscribers[event_type].remove(callback)

    def publish(self, event: Event) -> None:
        callbacks = self._subscribers.get(event.event_type, [])

        for callback in callbacks:
            try:
                callback(event)
            except Exception as exc:
                failure = SubscriberFailure(
                    event=event,
                    callback=callback,
                    exception=exc,
                )

                self.failures.append(failure)

                logger.exception(
                    "Event subscriber failed: event_type=%s, callback=%r",
                    event.event_type,
                    callback,
                )
