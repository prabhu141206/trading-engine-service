
---

# Module: Event Bus

## Purpose

The Event Bus provides communication between modules **without them knowing about each other**.

Example:

```text id="nsv98i"
MarketSessionManager

↓

Publish

MARKET_OPEN

↓

Event Bus

↓

SessionManager
```

The MarketSessionManager never imports or calls the SessionManager directly.

---

# Responsibility

Only three responsibilities.

1. Register subscribers.
2. Publish events.
3. Remove subscribers.

Nothing else.

It should **never**:

* Know about trading.
* Know about users.
* Know about strategies.
* Process events.
* Retry events.
* Store events permanently.

---

# Inputs

```text id="gt0o0e"
Event Type

Event Object
```

---

# Outputs

Notify all subscribers.

---

# Public API

I would keep it very small.

```python
class EventBus:

    def subscribe(...):
        ...

    def unsubscribe(...):
        ...

    def publish(...):
        ...
```

Only three public methods.

---

# Internal Data

Internally, the Event Bus only stores:

```text id="4g35zw"
Subscribers

{
    MARKET_OPEN: [...],

    MARKET_CLOSE: [...],

    CANDLE_COMPLETED: [...],

    EMA_UPDATED: [...]
}
```

A dictionary.

Key

↓

Event Type

Value

↓

List of Callbacks

---

# Internal Flow

## Subscribe

```text id="0fwgzz"
Subscriber

↓

subscribe()

↓

Dictionary Updated
```

---

## Publish

```text id="m4dg7t"
Publisher

↓

publish()

↓

Find Subscribers

↓

Call Each Subscriber
```

---

## Unsubscribe

```text id="4ajwxa"
Subscriber

↓

unsubscribe()

↓

Remove Callback
```

---

# Dependencies

None.

No market modules.

No scheduler.

No session manager.

No websocket.

It should be completely generic.

---

# Failure Cases

* Subscribe twice.
* Publish with no subscribers.
* Unsubscribe unknown callback.
* Subscriber throws an exception.

We should define how to handle each.

---

# Folder Structure

I would create a new package.

```text id="y2tsqn"
src/

event_system/

├── __init__.py
├── event_bus.py
├── event.py
├── event_type.py
├── tests/
```

Notice something.

I would **not** put the Event Bus inside `market_session`.

Because the Event Bus belongs to the **whole application**, not just market sessions.

---

# Event Object

Instead of publishing only:

```python
"MARKET_OPEN"
```

I recommend creating an Event model.

```python
@dataclass(frozen=True)
class Event:

    event_type: EventType

    payload: object | None

    timestamp: datetime
```

Now every event has a common structure.

Example:

```python
Event(
    event_type=EventType.MARKET_OPEN,
    payload=None,
    timestamp=...
)
```

Later:

```python
Event(
    event_type=EventType.CANDLE_COMPLETED,
    payload=candle,
    timestamp=...
)
```

The Event Bus doesn't care what's inside `payload`.

---

# Event Types

Create one enum.

```python
class EventType(Enum):

    MARKET_OPEN = ...

    MARKET_CLOSE = ...

    CANDLE_COMPLETED = ...

    EMA_UPDATED = ...

    SIGNAL_GENERATED = ...
```

Even though you'll only use two initially.

Future modules will reuse the same enum.

---

# Unit Tests

I would write these tests.

```text id="x6a4ij"
Subscribe

↓

Publish

↓

Subscriber Called
```

---

```text id="gqoktl"
Two Subscribers

↓

Publish

↓

Both Called
```

---

```text id="n6evfu"
Unsubscribe

↓

Publish

↓

Callback Not Called
```

---

```text id="xh0u43"
Publish

↓

No Subscribers

↓

No Exception
```

---

```text id="5wvduw"
Duplicate Subscribe

↓

Only One Registration
```

(or document that duplicates are allowed—pick one behavior and test it.)

---

## One design decision before coding

I recommend that the Event Bus be **synchronous** in Version 1.

Meaning:

```text id="dwjlwm"
publish()

↓

Immediately call every subscriber

↓

Return
```

No threads.

No queues.

No async.

Why?

Because your application already has multiple threads (Market Session Manager, later the market data pipeline). Keeping the Event Bus synchronous makes it much simpler to reason about and debug. If you later need asynchronous dispatching, you can change the internals without changing the public API. That's a solid foundation for Version 1.
