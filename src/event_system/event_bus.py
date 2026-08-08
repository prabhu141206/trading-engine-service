from collections import defaultdict
from collections.abc import Callable


from .event import Event
from .event_type import EventType



class EventBus:

    def __init__(self):
        self._subscribers = defaultdict(list)


    def subscribe(
        self,
        event_type: EventType,
        callback: Callable[[Event], None]
    ) -> None:

        if callback not in self._subscribers[event_type]:
            self._subscribers[event_type].append(callback)

    def unsubscribe(
        self,
        event_type: EventType,
        callback: Callable[[Event], None]
    ) -> None:

        if callback in self._subscribers[event_type]:
            self._subscribers[event_type].remove(callback)

    def publish(self, event: Event) -> None:

        callbacks = self._subscribers.get(event.event_type, [])

        for callback in callbacks:
            try:
                callback(event)
            except Exception as e:
                print(f"Subscriber error: {e}")