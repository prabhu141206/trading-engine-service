# Event System (Event Bus)

## Purpose

The **Event Bus** is a communication layer that allows independent services to exchange messages without directly calling each other.

Instead of one service knowing who should receive a message, it simply publishes an event. Any interested service can subscribe to that event and react automatically.

This pattern is called **Event-Driven Architecture**.

---

# Why Use an Event Bus?

Without an Event Bus:

```text
Service A ───────► Service B
```

Service A is tightly coupled to Service B. If Service B changes, Service A may also need changes.

With an Event Bus:

```text
Service A ─────► Event Bus ◄──── Service B
                         ◄──── Service C
                         ◄──── Service D
```

Service A does not know who receives the event. New subscribers can be added without modifying Service A.

---

# Core Concepts

## Publisher

A service that sends an event.

Example:

```text
Service A
```

---

## Subscriber

A service that listens for an event and reacts when it occurs.

Examples:

```text
Service B
Service C
Service D
```

---

## Event Type

Identifies what happened.

Examples:

* USER_CREATED
* PAYMENT_SUCCESS
* ORDER_PLACED
* FILE_UPLOADED

---

## Event Payload

Additional information attached to the event.

Example:

```json
{
  "user_id": 101,
  "email": "user@example.com"
}
```

---

# High-Level Flow

```text
Service A
    │
    │ Publish Event
    ▼
Event Bus
   ├────────► Service B
   ├────────► Service C
   └────────► Service D
```

Steps:

1. Service A publishes an event.
2. Event Bus receives the event.
3. Event Bus finds all subscribers interested in that event type.
4. Event Bus delivers the event to each subscriber.
5. Each subscriber processes the event independently.

---

# Example Scenario

Suppose a new user registers.

## Published Event

```text
USER_CREATED
```

## Subscribers

* Email Service → sends welcome email
* Analytics Service → records signup metrics
* Notification Service → creates notification

The registration service does not call any of these services directly.

---

# Subscriber Registry

The Event Bus internally maintains a mapping of event types to subscribers.

Conceptually:

```python
{
    "USER_CREATED": [email_service, analytics_service],
    "PAYMENT_SUCCESS": [invoice_service],
}
```

When `USER_CREATED` is published, both subscribers are executed.

---

# Advantages

* **Loose Coupling** – services remain independent.
* **Extensibility** – add new subscribers without changing publishers.
* **Testability** – publishers and subscribers can be tested separately.
* **Scalability** – event processing can be distributed later.
* **Clear Responsibilities** – each service handles only its own concern.

---

# Limitations

* Harder to trace execution flow compared to direct function calls.
* Errors in subscribers must be handled carefully.
* Ordering between subscribers is usually not guaranteed.
* Excessive events can make the system difficult to reason about.

---

# Minimal Conceptual API

```python
event_bus.subscribe("USER_CREATED", handle_user_created)

event_bus.publish(event)
```

---

# What This Module Demonstrates

This module demonstrates the fundamental building blocks of an event-driven system:

* Event definition
* Event type identification
* Subscriber registration
* Event publishing
* Event delivery to multiple subscribers

The implementation is intentionally kept generic so it can be reused in any backend system, not just trading applications.

---

# Summary

An **Event Bus** acts as a central communication channel between publishers and subscribers. Publishers emit events, subscribers listen for events, and the Event Bus routes messages between them. This enables a loosely coupled architecture where services can evolve independently while still communicating efficiently.
