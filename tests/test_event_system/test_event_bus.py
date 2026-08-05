from event_system.event_bus import EventBus
from event_system.event import Event
from event_system.event_type import EventType


# Test 1 - Subscribe & Publish
# This verifies that a subscriber receives an event.
def test_subscribe_and_publish():

    bus = EventBus()
    received = []

    def callback(event):
        received.append(event)

    bus.subscribe(EventType.MARKET_OPEN, callback)

    bus.publish(Event(EventType.MARKET_OPEN))

    assert len(received) == 1
    assert received[0].event_type == EventType.MARKET_OPEN

# Test 2 - Multiple Subscribers
def test_multiple_subscribers():

    bus = EventBus()

    subscriber_1 = []
    subscriber_2 = []

    def callback_1(event):
        subscriber_1.append(event)

    def callback_2(event):
        subscriber_2.append(event)

    bus.subscribe(EventType.MARKET_OPEN, callback_1)
    bus.subscribe(EventType.MARKET_OPEN, callback_2)

    bus.publish(Event(EventType.MARKET_OPEN))

    assert len(subscriber_1) == 1
    assert len(subscriber_2) == 1

# Test 3 - Unsubscribe
def test_unsubscribe():

    bus = EventBus()

    received = []

    def callback(event):
        received.append(event)

    bus.subscribe(EventType.MARKET_OPEN, callback)

    bus.unsubscribe(EventType.MARKET_OPEN, callback)

    bus.publish(Event(EventType.MARKET_OPEN))

    assert len(received) == 0

#Test 4 - Duplicate Subscribe
def test_duplicate_subscribe():

    bus = EventBus()

    received = []

    def callback(event):
        received.append(event)

    bus.subscribe(EventType.MARKET_OPEN, callback)
    bus.subscribe(EventType.MARKET_OPEN, callback)

    bus.publish(Event(EventType.MARKET_OPEN))

    assert len(received) == 1


# Test 5 - Publish With No Subscribers
def test_publish_without_subscribers():

    bus = EventBus()

    bus.publish(Event(EventType.MARKET_OPEN))

# Test 6 - Subscriber Exception
def test_subscriber_exception_does_not_stop_others():

    bus = EventBus()

    received = []

    def bad_callback(event):
        raise RuntimeError("Subscriber failed")

    def good_callback(event):
        received.append(event)

    bus.subscribe(EventType.MARKET_OPEN, bad_callback)
    bus.subscribe(EventType.MARKET_OPEN, good_callback)

    bus.publish(Event(EventType.MARKET_OPEN))

    assert len(received) == 1

    