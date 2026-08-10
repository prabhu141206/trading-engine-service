# Market Session Manager

## Purpose

`MarketSessionManager` controls the **market lifecycle** of the trading system.

It continuously asks `MarketScheduler` for the next market event, waits until that event occurs, and publishes the event through `EventBus`.

This component contains **no market timing business logic**. All exchange timings, holidays, and weekend rules belong to `MarketScheduler`.

---

## Responsibilities

* Ask `MarketScheduler` for the next market event.
* Maintain the current market state (`OPEN` or `CLOSED`).
* Wait until the scheduled event time.
* Publish market lifecycle events through `EventBus`.
* Continue the lifecycle loop until `stop()` is called.

---

## What this module does NOT do

* User session management
* Symbol subscription management
* Market data handling
* Strategy execution
* Order placement
* Database access

Those responsibilities belong to other modules.

---

## Dependencies

### Internal dependencies

* `event_system.event`
* `event_system.event_bus`
* `event_system.event_type`
* `market_session.market_scheduler`
* `market_session.market_state`
* `market_session.market_config`
* `market_session.models`

### External dependencies

* Python `threading`
* Python `datetime`

---

## Market states

The market can only be in one of two states:

```python
class MarketState(Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
```

> **Note:** `WAITING` is not a market state. Waiting is an internal behavior of the manager while it sleeps until the next scheduled event.

---

## High-level flow

```text
main.py
   ↓
MarketSessionManager.start()
   ↓
_run()
   ↓
MarketScheduler.get_next_event()
   ↓
Update market state
   ↓
Wait until event time
   ↓
Publish event through EventBus
   ↓
Repeat
```

---

## Runtime sequence

### Before market open (08:00)

```text
Current state: CLOSED
Next event   : MARKET_OPEN at 09:15
Action       : Wait
```

### Market opens (09:15)

```text
Publish MARKET_OPEN
State becomes OPEN
```

### During market hours (11:00)

```text
Current state: OPEN
Next event   : MARKET_CLOSE at 15:30
Action       : Wait
```

### Market closes (15:30)

```text
Publish MARKET_CLOSE
State becomes CLOSED
```

---

## Startup during market hours

This feature was added to handle application startup while the market is already open.

### Example

* Application starts at **11:00 AM**
* Scheduler reports:

  * `market_state = OPEN`
  * next event = `MARKET_CLOSE`

### Behavior

Immediately after startup:

```text
Publish MARKET_OPEN
```

Then the manager waits until market close and later publishes:

```text
MARKET_CLOSE
```

### Why this is important

Without this bootstrap event, subscribers such as `SessionManager` would not create runtime sessions until the next trading day.

---

## Event publishing

Published events:

| Event          | Meaning                 |
| -------------- | ----------------------- |
| `MARKET_OPEN`  | Trading session started |
| `MARKET_CLOSE` | Trading session ended   |

Events are published without payload:

```python
SystemEvent(event_type=EventType.MARKET_OPEN)
```

---

## Thread model

* Runs in a dedicated daemon thread named `MarketSessionManager`.
* Uses `threading.Event` for interruptible waiting.
* `stop()` immediately interrupts any active wait.

---

## Public API

### Start manager

```python
manager.start()
```

### Stop manager

```python
manager.stop()
```

### Read current state

```python
manager.market_state
```

Returns `MarketState.OPEN` or `MarketState.CLOSED`.

---

## Design principles

### Single responsibility

* **Scheduler** decides *when* market events occur.
* **Manager** decides *when to publish* them.

### Event-driven communication

The manager never calls downstream services directly; it communicates only through `EventBus`.

### Idempotent startup

Bootstrap `MARKET_OPEN` is published only once per application startup.

### Testability

The scheduling loop is separated into `_process_one_iteration()` so unit tests can execute a single cycle deterministically.

---

## Typical integration

```python
event_bus = EventBus()
scheduler = MarketScheduler()

manager = MarketSessionManager(
    scheduler=scheduler,
    event_bus=event_bus
)

manager.start()
```

A subscriber can react to market open:

```python
event_bus.subscribe(
    EventType.MARKET_OPEN,
    session_manager._on_market_open
)
```

---

## Example timeline

### Normal startup before market open

```text
08:00 start
09:15 MARKET_OPEN
15:30 MARKET_CLOSE
```

### Startup during market hours

```text
11:00 start
11:00 MARKET_OPEN (bootstrap)
15:30 MARKET_CLOSE
```

---

## Testing

The module is covered by unit tests for:

* market open cycle
* market close cycle
* interruptible waiting
* start/stop lifecycle
* startup during market hours
* market state transitions

Run tests:

```bash
python -m pytest tests/test_market_sessions -v
```

---

## Future enhancements

Planned future capabilities:

* exchange-specific sessions
* pre-open and post-close support
* observability metrics
* structured logging
* health endpoints
* distributed leader election for HA deployments

These features are intentionally excluded from the current implementation to keep the lifecycle manager focused and maintainable.

---

## Summary

`MarketSessionManager` is a lightweight event-driven orchestrator that:

* tracks market state,
* waits for scheduled market events,
* publishes lifecycle events,
* supports startup during active trading sessions,
* and remains isolated from business logic and trading execution concerns.

This separation makes the market lifecycle predictable, testable, and easy to extend as the trading engine grows.
