# Session Manager

## Purpose

The **SessionManager** is responsible for managing all active user sessions during market hours.

It listens for market lifecycle events from the `EventBus` and creates or destroys `UserSession` objects accordingly.

The SessionManager is the first major consumer in the event-driven architecture of the trading engine.

---

# Responsibilities

* Subscribe to market lifecycle events.
* Create `UserSession` objects when the market opens.
* Store active user sessions in memory.
* Remove all active user sessions when the market closes.
* Provide access to active sessions.

---

# Not Responsible For

The SessionManager does **not**:

* Decide market timings.
* Publish market events.
* Manage WebSocket subscriptions.
* Execute trading strategies.
* Process market data.
* Execute trades.
* Persist sessions to a database.

These responsibilities belong to other modules.

---

# Dependencies

* EventBus
* EventType
* Event
* UserSession

---

# Input

The SessionManager receives events from the `EventBus`.

### MARKET_OPEN

Triggered when the market opens.

### MARKET_CLOSE

Triggered when the market closes.

---

# Processing

## On MARKET_OPEN

1. Load active users.
2. Create a `UserSession` for each user.
3. Store sessions in memory.

## On MARKET_CLOSE

1. Clear all active sessions.
2. Release session resources.

---

# Output

The SessionManager maintains an in-memory session registry.

Example:

```python
{
    101: UserSession(...),
    202: UserSession(...),
    303: UserSession(...),
}
```

---

# Internal State

```python
_sessions: dict[int, UserSession]
```

This dictionary contains all currently active user sessions.

---

# Public API

```python
start()
```

Version 1 exposes only the event subscription entry point. Additional query APIs can be added later.

---

# Internal Methods

```python
_on_market_open()

_on_market_close()

_load_active_users()

_create_session()
```

---

# Workflow

## Market Open

```text
MARKET_OPEN
      │
      ▼
EventBus
      │
      ▼
SessionManager
      │
      ▼
Load Active Users
      │
      ▼
Create UserSession Objects
      │
      ▼
Store in _sessions
```

---

## Market Close

```text
MARKET_CLOSE
      │
      ▼
EventBus
      │
      ▼
SessionManager
      │
      ▼
Clear _sessions
      │
      ▼
No Active Sessions
```

---

# Event Flow

```text
MarketSessionManager
        │
 Publish MARKET_OPEN
        ▼
EventBus
        │
        ▼
SessionManager
        │
        ▼
UserSession Objects
```

The publisher and subscriber do not know about each other directly. Communication happens only through the `EventBus`.

---

# UserSession (Version 1)

```python
class UserSession:
    user_id: int
```

Version 1 stores only the user identifier. Strategy runtimes and additional dependencies will be added in later modules.

---

# Why Event-Driven?

Without an EventBus:

```text
MarketSessionManager
      │
      ▼
SessionManager
```

With an EventBus:

```text
MarketSessionManager
      │
      ▼
EventBus
      │
      ▼
SessionManager
```

Benefits:

* Loose coupling
* Easier testing
* Easier extensibility
* Independent module development

---

# Testing

## Unit Tests

* Verify MARKET_OPEN subscription.
* Verify MARKET_CLOSE subscription.
* Verify sessions are created on MARKET_OPEN.
* Verify sessions are removed on MARKET_CLOSE.

## Integration Test

Verified flow:

```text
EventBus.publish(MARKET_OPEN)
        │
        ▼
SessionManager._on_market_open()
        │
        ▼
Create UserSession Objects
        │
        ▼
Populate _sessions
```

This confirms that event publishing correctly triggers session creation.

---

# Design Principles

* Single Responsibility Principle (SRP)
* Event-Driven Architecture
* Dependency Injection
* In-Memory Session Registry
* Separation of Concerns
* Loose Coupling

---

# Current Limitations (Version 1)

* Users are loaded from a temporary in-memory list.
* Sessions are not persisted.
* No strategy runtime is attached yet.
* No symbol subscription management yet.
* No authentication integration yet.

These features will be added in later modules.

---

# Future Extensions

Planned enhancements:

* Database-backed user loading
* Session query APIs
* StrategyRuntime attachment
* SubscriptionRegistry integration
* Session metrics and monitoring
* Graceful session shutdown

---

# Summary

The **SessionManager** is the component responsible for maintaining the lifecycle of active user sessions.

It reacts to `MARKET_OPEN` and `MARKET_CLOSE` events published through the `EventBus`, creates `UserSession` objects when the market opens, stores them in memory, and removes them when the market closes.

This module establishes the first complete event-driven business workflow in the trading engine and forms the foundation for multi-user strategy execution in later modules.
