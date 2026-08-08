# Market Session Manager

## Purpose

The **MarketSessionManager** is responsible for controlling the market session lifecycle.

It continuously asks the `MarketScheduler` for the next market event, waits until that event occurs, and publishes the event through the `EventBus`.

It does **not** contain any market timing logic. All business rules related to market timings, holidays, and weekends belong to the `MarketScheduler`.

---

# Responsibilities

* Ask the `MarketScheduler` for the next market event.
* Update the current market state using the scheduler's result.
* Wait until the scheduled event time.
* Publish the event through the `EventBus`.
* Run continuously until the service is stopped.

---

# Not Responsible For

The MarketSessionManager does **not**:

* Calculate market timings.
* Check holidays.
* Check weekends.
* Decide whether the market is open or closed.
* Manage user sessions.
* Handle WebSocket connections.
* Execute trading strategies.

These responsibilities belong to other modules.

---

# Dependencies

* MarketScheduler
* EventBus
* EventType
* NextMarketEvent

---

## Input

The `MarketSessionManager` receives input from the `MarketScheduler`.

Every scheduling cycle, it calls:

```python
next_event = scheduler.get_next_event(current_time)
```

The scheduler returns a `NextMarketEvent` object.

```text
NextMarketEvent
│
├── event
│     ├── MARKET_OPEN
│     └── MARKET_CLOSE
│
├── event_time
│     └── Exact date & time of the next event
│
├── sleep_seconds
│     └── Number of seconds to wait
│
└── market_state
      ├── WAITING
      ├── OPEN
      └── CLOSED
```

### Meaning of each field

* **event** → Which event should be published after waiting.
* **event_time** → When that event should occur.
* **sleep_seconds** → How long the manager should wait before publishing.
* **market_state** → The current market state calculated by the `MarketScheduler`.

The `MarketSessionManager` does not calculate any of these values. It simply consumes them.


---

# Output

The manager publishes events through the `EventBus`.

Examples:

* MARKET_OPEN
* MARKET_CLOSE

These events are consumed by other modules such as the `SessionManager`.

---

# Internal State

The manager maintains the following internal state:

* running status
* background thread
* stop event
* current market state

---

# Public API

```python
start()

stop()
```

---

# Private Methods

```python
_run()

_process_one_iteration()

_wait()

_publish()
```

---

# Workflow

```
Start Service
      │
      ▼
Background Thread Starts
      │
      ▼
Ask MarketScheduler
      │
      ▼
Receive NextMarketEvent
      │
      ▼
Update Current Market State
      │
      ▼
Wait Until Event Time
      │
      ▼
Publish Event
      │
      ▼
Repeat
```

---

# Event Flow

```
MarketScheduler
        │
        ▼
NextMarketEvent
        │
        ▼
MarketSessionManager
        │
        ▼
EventBus.publish()
        │
        ▼
Subscribers
```

---

# Market State Ownership

The `MarketScheduler` is the single source of truth for the market state.

The `MarketSessionManager` only stores the state returned by the scheduler.

It never decides whether the market is waiting, open, or closed.

---

# Thread Lifecycle

```
start()

↓

Create Background Thread

↓

_run()

↓

Loop Until stop()

↓

stop()

↓

Wake Waiting Thread

↓

Exit Thread
```

---

# Testing

## Unit Tests

* Verify MARKET_OPEN processing.
* Verify MARKET_CLOSE processing.
* Verify market state updates.
* Verify `_wait()` timeout behavior.
* Verify `_wait()` interruption.
* Verify `start()`.
* Verify `stop()`.

## Integration Test

Verified integration:

```
FakeScheduler
      │
      ▼
MarketSessionManager
      │
      ▼
EventBus
      │
      ▼
Subscriber
```

This confirms that the manager successfully publishes events through the `EventBus`.

---

# Design Principles

* Single Responsibility Principle (SRP)
* Dependency Injection
* Event-Driven Architecture
* Separation of Concerns
* Interruptible background worker using `threading.Event`
* Scheduler owns all market timing and state logic

---

# Summary

The `MarketSessionManager` is a background worker responsible for executing the schedule provided by the `MarketScheduler`.

Its only responsibilities are to:

1. Obtain the next scheduled market event.
2. Update the current market state.
3. Wait until the event occurs.
4. Publish the event through the `EventBus`.
5. Repeat until the service is stopped.

It serves as the bridge between market scheduling and the event-driven components of the trading engine.

---

## Event System Integration

### Role in Event-Driven Architecture

The **MarketSessionManager** acts as a **publisher** in the event-driven architecture.

It does not know which services are interested in market events. Its responsibility is only to publish market lifecycle events through the `EventBus`.

### Published Events

* `MARKET_OPEN`
* `MARKET_CLOSE`

### Integration Flow

```text
MarketScheduler
      │
      ▼
MarketSessionManager
      │ Publish Event
      ▼
EventBus
      │
      ▼
Interested Subscribers
```

At this stage, the document focuses on the publisher side of the architecture. Subscribers are introduced in later modules.

