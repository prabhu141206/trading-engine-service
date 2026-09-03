
# Signal Distribution

The `signal_distribution` module is responsible for distributing strategy
signals to the users subscribed to the corresponding strategy group.

The signal distribution layer sits between strategy signal generation and
signal delivery.

It does not generate trading signals and does not contain strategy logic.

---

# 1. Purpose

The `signal_distribution` module is responsible for:

- Receiving generated strategy signals.
- Identifying users subscribed to the corresponding strategy group.
- Delivering the signal to the appropriate users.
- Keeping user-specific signal distribution separate from strategy logic.

The module does not determine whether a signal is a BUY, SELL, ENTRY, or
EXIT. That decision has already been made by the strategy layer.

The module answers a different question:

> Which users should receive this signal?

---

# 2. Architecture

The signal distribution flow is:

```text
                Strategy
                   │
                   ▼
             StrategyOutput
                   │
                   ▼
      STRATEGY_SIGNAL_GENERATED
                   │
                   ▼
          SignalDistributor
                   │
                   ▼
       StrategyUserRegistry
                   │
                   ▼
            User IDs
                   │
                   ▼
            SignalDelivery
````

The separation can be represented as:

```text
Strategy Layer
      │
      │ What signal was generated?
      ▼
Strategy Signal
      │
      ▼
Signal Distribution Layer
      │
      │ Who should receive it?
      ▼
Signal Delivery
```

---

# 3. Components

The signal distribution layer currently contains two main responsibilities:

```text
signal_distribution/
│
├── signal_distributor.py
└── signal_delivery.py
```

The major components are:

```text
SignalDistributor
SignalDelivery
```

The `StrategyUserRegistry` is part of the registry layer and is used by the
`SignalDistributor` to determine which users are subscribed to a strategy
group.

---

# 4. SignalDistributor

`SignalDistributor` is responsible for receiving strategy signal events and
distributing them to the appropriate users.

It subscribes to:

```text
STRATEGY_SIGNAL_GENERATED
```

When the event is received, the distributor:

1. Extracts the strategy signal.
2. Identifies the strategy group associated with the signal.
3. Queries the `StrategyUserRegistry` for subscribed users.
4. Sends the signal to each subscribed user through `SignalDelivery`.

Conceptually:

```text
STRATEGY_SIGNAL_GENERATED
          │
          ▼
   SignalDistributor
          │
          ▼
StrategyUserRegistry
          │
          ▼
    Matching Users
          │
          ▼
   SignalDelivery
```

---

# 5. StrategyUserRegistry

`StrategyUserRegistry` maintains the runtime relationship between strategy
groups and users.

For example:

```text
EMA + NIFTY + 5m + period 10
            │
            ├── User 101
            └── User 202
```

When a strategy generates a signal for this strategy group, the
`SignalDistributor` uses the registry to identify:

```text
101
202
```

The signal is then delivered only to those users.

The registry therefore acts as the runtime lookup between:

```text
StrategyGroup → Users
```

---

# 6. SignalDelivery

`SignalDelivery` is responsible for the actual delivery operation.

The distributor calls:

```python
delivery.deliver(user_id, signal)
```

The distributor does not need to know how delivery is implemented.

This creates a separation between:

```text
Who should receive the signal?
        │
        ▼
SignalDistributor

How should the signal be delivered?
        │
        ▼
SignalDelivery
```

This allows the delivery mechanism to evolve independently from the
distribution logic.

For example, a future delivery implementation could use a WebSocket or
another communication mechanism without changing the strategy or registry
layers.

---

# 7. Signal Distribution Flow

A complete signal flow looks like this:

```text
StrategyEngine
      │
      ▼
Concrete Strategy
      │
      ▼
StrategyOutput
      │
      ▼
STRATEGY_SIGNAL_GENERATED
      │
      ▼
SignalDistributor
      │
      ▼
StrategyUserRegistry
      │
      ▼
Subscribed User IDs
      │
      ├──────────────┐
      ▼              ▼
User 101          User 202
      │              │
      ▼              ▼
SignalDelivery   SignalDelivery
```

Only users subscribed to the matching strategy group receive the signal.

---

# 8. Matching Strategy Groups

Signals are distributed according to the strategy group associated with the
signal.

For example:

```text
Strategy Group:

EMA + NIFTY + 5m + period 10
```

has:

```text
User 101
User 202
```

as subscribers.

A generated signal for that strategy group is delivered to:

```text
User 101
User 202
```

but not to:

```text
User 303
```

if User 303 is subscribed to a different strategy group.

---

# 9. Multiple Users

Multiple users can subscribe to the same strategy group.

For example:

```text
EMA + NIFTY + 5m + period 10
            │
            ├── User 101
            ├── User 202
            └── User 303
```

The strategy computation itself does not need to be repeated for each user.

The strategy is computed once, and the resulting signal is distributed to
all matching subscribers.

This separates:

```text
Strategy Computation
```

from:

```text
User Distribution
```

---

# 10. No Matching Subscribers

A strategy signal may be generated when there are no users subscribed to
that strategy group.

In this case:

```text
Strategy Signal
      │
      ▼
SignalDistributor
      │
      ▼
No Subscribers
      │
      ▼
No Delivery
```

The distributor does not create a new subscription or modify the strategy
registry.

The signal simply has no users to receive it.

---

# 11. Same Signal Object

When a signal has multiple subscribers, the same signal object can be
delivered to each matching user.

Conceptually:

```text
                    Strategy Signal
                          │
             ┌────────────┼────────────┐
             ▼            ▼            ▼
          User 101     User 202     User 303
             │            │            │
             ▼            ▼            ▼
        SignalDelivery SignalDelivery SignalDelivery
```

The distribution layer therefore does not create separate strategy
calculations for each user.

---

# 12. Separation of Responsibilities

The signal distribution architecture intentionally separates several
responsibilities.

## Strategy

Responsible for:

```text
Market information
       ↓
Trading decision
       ↓
StrategyOutput
```

## SignalDistributor

Responsible for:

```text
Strategy Signal
       ↓
Find matching users
       ↓
Distribute signal
```

## StrategyUserRegistry

Responsible for:

```text
StrategyGroup
       ↓
Subscribed Users
```

## SignalDelivery

Responsible for:

```text
User + Signal
       ↓
Delivery mechanism
```

This keeps each component focused on one responsibility.

---

# 13. Relationship With Strategy Layer

The strategy layer produces the signal:

```text
Strategy
   ↓
StrategyOutput
   ↓
STRATEGY_SIGNAL_GENERATED
```

The signal distribution layer consumes it:

```text
STRATEGY_SIGNAL_GENERATED
   ↓
SignalDistributor
   ↓
StrategyUserRegistry
   ↓
SignalDelivery
```

The strategy does not need to know anything about users.

Likewise, the signal distributor does not need to know how the strategy
made its trading decision.

---

# 14. Relationship With Registry Layer

The signal distribution layer uses the `StrategyUserRegistry` as its source
of runtime subscription information.

```text
StrategyUserRegistry
        │
        │ StrategyGroup → Users
        ▼
SignalDistributor
        │
        ▼
SignalDelivery
```

The registry is populated by the session layer during runtime
initialization.

This means the signal distributor does not query PostgreSQL to determine
user subscriptions.

---

# 15. Database Boundary

`SignalDistributor` does not directly access PostgreSQL.

The database configuration is loaded earlier in the application lifecycle:

```text
PostgreSQL
    │
    ▼
UserSessionRepository
    │
    ▼
UserSession
    │
    ▼
SessionManager
    │
    ▼
StrategyUserRegistry
    │
    ▼
SignalDistributor
```

During real-time signal distribution, the distributor uses the in-memory
registry.

The database is therefore outside the real-time signal delivery path.

---

# 16. Event-Based Communication

The strategy and signal distribution layers communicate through the
application event system.

The strategy layer publishes:

```text
STRATEGY_SIGNAL_GENERATED
```

The signal distributor subscribes to that event.

Conceptually:

```text
StrategyEngine
      │
      │ publish
      ▼
   EventBus
      │
      │ STRATEGY_SIGNAL_GENERATED
      ▼
SignalDistributor
```

This keeps the strategy engine decoupled from the signal distribution
implementation.

The strategy engine does not directly call `SignalDistributor`.

---

# 17. Runtime Lifecycle

The signal distribution components operate using runtime state.

At market startup:

```text
Market Open
    │
    ▼
SessionManager
    │
    ▼
StrategyUserRegistry populated
```

During market hours:

```text
Strategy Signal
      │
      ▼
SignalDistributor
      │
      ▼
StrategyUserRegistry
      │
      ▼
SignalDelivery
```

At market close, the runtime session and registries are cleared.

Persistent subscription configuration remains stored in PostgreSQL.

---

# 18. Testing

The signal distribution layer has tests covering:

## Single User

Verifies that a signal is delivered to a subscribed user.

## Multiple Users

Verifies that a signal is delivered to all users subscribed to the matching
strategy group.

## Unsubscribed Users

Verifies that users who are not subscribed do not receive the signal.

## Strategy Group Matching

Verifies that a signal is delivered only to users belonging to the
corresponding strategy group.

## No Subscribers

Verifies that a signal with no subscribers does not cause a delivery.

## Same Signal Object

Verifies that the same signal object can be delivered to each matching
subscriber.

## Integration

Integration tests verify that:

```text
STRATEGY_SIGNAL_GENERATED
          │
          ▼
SignalDistributor
          │
          ▼
StrategyUserRegistry
          │
          ▼
SignalDelivery
```

works correctly as an event-driven flow.

---

# 19. Important Design Decisions

## 19.1 Signal distribution is separate from strategy execution

The strategy determines the trading decision.

The signal distribution layer determines which users receive that decision.

This prevents user management concerns from entering strategy logic.

---

## 19.2 SignalDistributor does not query the database

The distributor uses the runtime `StrategyUserRegistry`.

Persistent configuration is loaded into runtime state by the session/database
layers.

This keeps database access outside the real-time signal path.

---

## 19.3 Strategy computation is independent of user count

If ten users subscribe to the same strategy group, the strategy does not
need to execute ten times.

Instead:

```text
One Strategy Computation
        │
        ▼
One Strategy Signal
        │
        ▼
Ten User Deliveries
```

This separates computation from distribution.

---

## 19.4 Signal delivery is abstracted

`SignalDistributor` does not directly depend on a specific communication
mechanism.

It delegates the delivery operation to `SignalDelivery`.

This allows the delivery mechanism to change without changing the signal
distribution logic.

---

## 19.5 Event-driven communication

The strategy layer and signal distribution layer communicate through the
`EventBus`.

The strategy engine publishes an event rather than directly invoking the
signal distributor.

This reduces coupling between components.

---

## 19.6 No user-specific strategy execution

Strategies operate at the strategy-group level rather than executing
separately for every user.

User-specific behavior begins at the signal distribution stage.

---

# Overall Signal Distribution Flow

The complete signal distribution architecture can be summarized as:

```text
                         Strategy
                            │
                            ▼
                     StrategyOutput
                            │
                            ▼
             STRATEGY_SIGNAL_GENERATED
                            │
                            ▼
                       EventBus
                            │
                            ▼
                   SignalDistributor
                            │
                            ▼
                  StrategyUserRegistry
                            │
                            ▼
                     Matching Users
                            │
              ┌─────────────┼─────────────┐
              ▼             ▼             ▼
           User 101      User 202      User 303
              │             │             │
              ▼             ▼             ▼
       SignalDelivery  SignalDelivery  SignalDelivery
```

The signal distribution layer therefore acts as the **bridge between
strategy signal generation and user-specific signal delivery**.

It identifies the users subscribed to the strategy that generated the
signal and delegates the actual delivery operation without coupling
strategy logic to users or communication mechanisms.


