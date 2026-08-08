# Event System

## Purpose

The **Event System** provides communication between independent modules of the trading engine.

Instead of modules calling each other directly, they communicate by publishing and subscribing to events through the `EventBus`.

This keeps modules loosely coupled, easier to maintain, and easier to test.

---

# Responsibilities

* Register subscribers for specific event types.
* Publish events to all interested subscribers.
* Decouple producers from consumers.
* Deliver events in the order they are published.
* Maintain thread-safe event registration and publishing.

---

# Not Responsible For

The Event System does **not**:

* Execute business logic.
* Store market data.
* Manage user sessions.
* Process trading strategies.
* Calculate indicators.
* Execute trades.

Its only responsibility is event communication.

---

# Components

```text
event_system/

├── event.py
├── event_type.py
└── event_bus.py
```

---

# Component Responsibilities

## Event

Represents a single event flowing through the system.

### Fields

```python
event_type
payload
```

### Example

```text
Event
│
├── event_type = MARKET_OPEN
└── payload = NextMarketEvent(...)
```

---

## EventType

Defines every event that can exist in the trading engine.

It is the **single source of truth** for all event names.

### Example

```python
MARKET_OPEN
MARKET_CLOSE
```

As the project grows, new events will be added here.

Examples:

* CANDLE_COMPLETED
* EMA_UPDATED
* SIGNAL_GENERATED
* ORDER_PLACED
* ORDER_FILLED

---

## EventBus

Acts as the communication hub.

It receives events from producers and delivers them to all registered subscribers.

---

# Input

The EventBus receives an `Event` object.

```text
Event
│
├── event_type
└── payload
```

The event can originate from any producer module.

Examples:

* MarketSessionManager
* CandleBuilder
* IndicatorEngine
* TradingEngine

---

# Processing

When an event is published:

1. Read the event type.
2. Find all subscribers registered for that event.
3. Execute each subscriber callback.
4. Return after all callbacks finish.

---

# Output

The EventBus does not return data.

Its output is the execution of subscriber callbacks.

```text
EventBus

↓

Subscriber A

↓

Subscriber B

↓

Subscriber C
```

---

# Architecture Flow

```text
Producer

↓

Event

↓

EventBus

↓

Subscribers
```

---

# Publish Flow

```text
MarketSessionManager

↓

Publish MARKET_OPEN

↓

EventBus

↓

SessionManager

↓

Create User Sessions
```

---

# Subscribe Flow

```text
SessionManager

↓

Subscribe

↓

MARKET_OPEN

↓

Wait for notification
```

---

# Why EventBus?

Without an EventBus:

```text
MarketSessionManager

↓

SessionManager

↓

MarketDataPipeline

↓

TradingEngine
```

Every module directly depends on another module.

With an EventBus:

```text
Producer

↓

EventBus

↓

Consumers
```

Modules no longer need to know who is listening.

---

# Benefits

* Loose coupling
* Easy module replacement
* Better scalability
* Easier testing
* Event-driven architecture
* Independent module development

---

# Thread Safety

The EventBus is thread-safe.

Multiple modules can publish or subscribe without corrupting the subscriber registry.

Synchronization is handled internally by the EventBus.

---

# Public API

```python
subscribe()

unsubscribe()

publish()
```

---

# Internal Data

The EventBus maintains a subscriber registry.

Conceptually:

```text
{
    MARKET_OPEN: [
        callback1,
        callback2
    ],

    MARKET_CLOSE: [
        callback3
    ]
}
```

---

# Unit Tests

Verified:

* Subscribe registers callbacks.
* Publish notifies subscribers.
* Multiple subscribers receive the same event.
* Unsubscribe removes callbacks.
* Publishing without subscribers does not fail.

---

# Integration Test

Verified integration:

```text
FakeScheduler

↓

MarketSessionManager

↓

EventBus

↓

Subscriber
```

This confirms that events published by the `MarketSessionManager` are correctly delivered through the `EventBus`.

---

# Design Principles

* Single Responsibility Principle (SRP)
* Publish–Subscribe Pattern
* Dependency Injection
* Event-Driven Architecture
* Loose Coupling
* Thread Safety

---

# Summary

The Event System is the communication backbone of the trading engine.

It enables independent modules to exchange information without direct dependencies.

Every producer publishes events to the `EventBus`, and every consumer subscribes only to the events it needs.

This architecture allows the trading engine to remain modular, scalable, and easy to extend as new components are added.
