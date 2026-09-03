
# Module 4 — Registry

The Registry module maintains runtime configuration and relationships
required by the trading engine.

The Registry module contains three runtime registries:

- `SubscriptionRegistry`
- `StrategyRegistry`
- `StrategyUserRegistry`

These registries store runtime state required by other components.

They do not perform external operations such as WebSocket connections,
database access, or strategy execution.

---

# 1. Objective

The main purpose of the Registry module is to provide centralized,
in-memory runtime state for the trading engine.

The three registries have different responsibilities:

```text
SubscriptionRegistry
        │
        └── Which symbols are required?

StrategyRegistry
        │
        └── Which strategy configurations should run?

StrategyUserRegistry
        │
        └── Which users are subscribed to each strategy?
````

Together, they provide the runtime configuration required by the market
data, strategy, and signal distribution components.

---

# 2. Responsibilities

## SubscriptionRegistry

Responsible for:

* Registering required market symbols.
* Maintaining unique symbols.
* Removing symbols.
* Providing registered symbols to `MarketDataManager`.
* Clearing runtime subscription state.

---

## StrategyRegistry

Responsible for:

* Registering unique strategy configurations.
* Preventing duplicate strategy groups.
* Removing strategy configurations.
* Providing strategy configurations to `StrategyEngine`.
* Clearing runtime strategy state.

---

## StrategyUserRegistry

Responsible for:

* Maintaining the relationship between strategy groups and users.
* Registering users for strategy groups.
* Removing user subscriptions from strategy groups.
* Returning users subscribed to a strategy group.
* Clearing runtime user-strategy subscription state.

The relationship maintained by this registry is:

```text
StrategyGroup → User IDs
```

For example:

```text
EMA + NIFTY + 5m + period 10
        │
        ├── User 101
        └── User 202
```

---

# 3. Architecture

The Registry module acts as a runtime state layer between the components
that populate configuration and the components that consume it.

```text
                         SessionManager
                              │
               ┌──────────────┼──────────────┐
               │              │              │
               ▼              ▼              ▼
       SubscriptionRegistry  StrategyRegistry  StrategyUserRegistry
               │              │              │
               ▼              ▼              ▼
       MarketDataManager  StrategyEngine  SignalDistributor
               │              │              │
               ▼              ▼              ▼
       WebSocketClient   StrategyFactory  SignalDelivery
```

The responsibilities are separated:

```text
SubscriptionRegistry
        │
        └── Market data configuration

StrategyRegistry
        │
        └── Strategy computation configuration

StrategyUserRegistry
        │
        └── User-to-strategy relationships
```

---

# 4. SubscriptionRegistry

## Purpose

`SubscriptionRegistry` maintains the unique symbols required by the active
runtime sessions.

For example:

```text
User 101 → NIFTY, BANKNIFTY

User 202 → NIFTY

User 303 → FINNIFTY
```

The registry stores:

```text
NIFTY
BANKNIFTY
FINNIFTY
```

Because the registry uses a `set`, duplicate symbols are automatically
removed.

For example, if both User 101 and User 202 require NIFTY, the registry
still contains only:

```text
NIFTY
```

---

# 4.1 SubscriptionRegistry API

```python
add_symbol(symbol)

remove_symbol(symbol)

get_symbols()

clear()
```

## `add_symbol()`

Registers a symbol.

Example:

```python
registry.add_symbol("NIFTY")
```

---

## `remove_symbol()`

Removes a symbol.

Example:

```python
registry.remove_symbol("NIFTY")
```

---

## `get_symbols()`

Returns all currently registered symbols.

Example:

```python
symbols = registry.get_symbols()
```

A copy is returned so callers cannot directly modify the internal
registry state.

---

## `clear()`

Removes all registered symbols.

This is used when the market session ends.

---

# 5. StrategyRegistry

## Purpose

`StrategyRegistry` maintains the unique strategy configurations required by
the trading engine.

For example:

```text
User 101 → EMA10 + NIFTY + 5m

User 202 → EMA10 + NIFTY + 5m

User 303 → EMA10 + FINNIFTY + 5m
```

The registry stores only:

```text
EMA10 + NIFTY + 5m

EMA10 + FINNIFTY + 5m
```

Therefore, multiple users can share the same strategy computation.

This prevents unnecessary duplicate strategy instances or calculations for
identical strategy configurations.

---

# 6. StrategyGroup

`StrategyGroup` represents the identity of one runtime strategy
configuration.

Example:

```python
StrategyGroup(
    strategy_type="EMA",
    symbol="NIFTY",
    timeframe="5m",
    parameters=(("period", 10),)
)
```

The main fields are:

| Field           | Description                  |
| --------------- | ---------------------------- |
| `strategy_type` | Strategy type                |
| `symbol`        | Symbol used by the strategy  |
| `timeframe`     | Strategy timeframe           |
| `parameters`    | Strategy-specific parameters |

`StrategyGroup` is immutable using `frozen=True`.

This allows strategy groups to be safely stored in a `set` and prevents
accidental modification after registration.

---

# 7. StrategyRegistry API

```python
add_strategy(group)

remove_strategy(group)

get_strategies()

clear()
```

## `add_strategy()`

Registers a strategy configuration.

Duplicate configurations are automatically ignored.

Example:

```python
strategy_registry.add_strategy(strategy_group)
```

---

## `remove_strategy()`

Removes a strategy configuration.

Example:

```python
strategy_registry.remove_strategy(strategy_group)
```

---

## `get_strategies()`

Returns all unique registered strategy groups.

A copy is returned to protect the internal registry state.

Example:

```python
strategies = strategy_registry.get_strategies()
```

---

## `clear()`

Removes all registered strategy groups.

---

# 8. StrategyUserRegistry

## Purpose

`StrategyUserRegistry` maintains the runtime relationship between a
strategy group and the users subscribed to that strategy.

For example:

```text
EMA + NIFTY + 5m + period 10
        │
        ├── User 101
        └── User 202
```

The registry allows one strategy computation to serve multiple users.

The strategy itself does not need to execute separately for every user.

---

# 8.1 StrategyUserRegistry API

```python
subscribe(user_id, strategy_group)

unsubscribe(user_id, strategy_group)

get_subscribers(strategy_group)

clear()
```

---

## `subscribe()`

Registers a user for a strategy group.

Example:

```python
strategy_user_registry.subscribe(
    user_id=101,
    strategy_group=ema_nifty,
)
```

---

## `unsubscribe()`

Removes a user's subscription from a strategy group.

Example:

```python
strategy_user_registry.unsubscribe(
    user_id=101,
    strategy_group=ema_nifty,
)
```

---

## `get_subscribers()`

Returns the users currently subscribed to a strategy group.

Example:

```python
users = strategy_user_registry.get_subscribers(
    ema_nifty
)
```

For example:

```text
EMA + NIFTY + 5m
        │
        ├── 101
        └── 202
```

returns:

```python
{101, 202}
```

A copy is returned so callers cannot directly modify the internal
subscription state.

---

## `clear()`

Removes all runtime strategy-user subscriptions.

This is used when the market session ends.

---

# 9. SessionManager Integration

`SessionManager` is responsible for populating the runtime registries when
the market opens.

The active user configuration is loaded into `UserSession` objects.

The flow is:

```text
MARKET_OPEN
     │
     ▼
SessionManager
     │
     ▼
_load_active_users()
     │
     ▼
UserSession
     │
     ├── subscribed_symbols
     │          │
     │          ▼
     │   SubscriptionRegistry
     │
     └── strategies
                │
                ├───────────────┐
                ▼               ▼
        StrategyRegistry   StrategyUserRegistry
```

For every `UserSession`, the `SessionManager` registers:

* The user's symbols in `SubscriptionRegistry`.
* The user's strategies in `StrategyRegistry`.
* The user's strategy subscriptions in `StrategyUserRegistry`.

Conceptually:

```python
for symbol in session.subscribed_symbols:
    subscription_registry.add_symbol(symbol)

for strategy in session.strategies:
    strategy_registry.add_strategy(strategy)

    strategy_user_registry.subscribe(
        session.user_id,
        strategy,
    )
```

This creates the complete runtime configuration.

---

# 10. MarketDataManager Integration

`MarketDataManager` reads the required symbols from
`SubscriptionRegistry`.

The registry does not directly communicate with `MarketDataManager` through
the `EventBus`.

The relationship is:

```text
SessionManager
      │
      │ writes
      ▼
SubscriptionRegistry
      │
      │ reads
      ▼
MarketDataManager
```

The `EventBus` is used for lifecycle notification.

For example:

```text
SessionManager
      │
      │ SESSIONS_READY
      ▼
EventBus
      │
      ▼
MarketDataManager
      │
      │ get_symbols()
      ▼
SubscriptionRegistry
      │
      ▼
WebSocketClient
```

The registry therefore stores the runtime configuration, while
`MarketDataManager` performs the actual market-data operations.

---

# 11. StrategyEngine Integration

`StrategyEngine` reads the unique strategy configurations from
`StrategyRegistry`.

The flow is:

```text
SessionManager
      │
      │ registers
      ▼
StrategyRegistry
      │
      │ get_strategies()
      ▼
StrategyEngine
      │
      ▼
StrategyFactory
      │
      ▼
Strategy Objects
```

`StrategyRegistry` does not create strategy objects.

Its responsibility ends at maintaining strategy configuration.

The creation and execution of strategies belong to the strategy layer.

---

# 12. SignalDistributor Integration

`SignalDistributor` uses `StrategyUserRegistry` to determine which users
should receive a generated strategy signal.

The flow is:

```text
StrategyEngine
      │
      ▼
STRATEGY_SIGNAL_GENERATED
      │
      ▼
SignalDistributor
      │
      │ get_subscribers(strategy_group)
      ▼
StrategyUserRegistry
      │
      ▼
User IDs
      │
      ▼
SignalDelivery
```

For example:

```text
EMA + NIFTY + 5m + period 10
            │
            ├── User 101
            └── User 202
```

When this strategy generates a signal, the `SignalDistributor` retrieves
the subscribers:

```python
users = strategy_user_registry.get_subscribers(
    strategy_group
)
```

The signal is then delivered to each matching user.

The Registry module therefore provides the runtime subscription lookup,
while the signal distribution module handles the actual distribution.

---

# 13. Registry Relationships

The three registries serve different purposes.

```text
SubscriptionRegistry
        │
        └── Symbol → Required market data


StrategyRegistry
        │
        └── StrategyGroup → Strategy computation


StrategyUserRegistry
        │
        └── StrategyGroup → Users
```

This separation is important.

For example:

```text
NIFTY
```

being registered does not tell us:

* Which strategy should run.
* Which users are subscribed.
* How the signal should be delivered.

Those responsibilities belong to the other registries and components.

---

# 14. Market Close

When the market closes, `SessionManager` clears the runtime state.

The flow is:

```text
MARKET_CLOSE
     │
     ▼
SessionManager
     │
     ├── clear sessions
     │
     ├── clear SubscriptionRegistry
     │
     ├── clear StrategyRegistry
     │
     └── clear StrategyUserRegistry
```

This ensures that the registries contain only the runtime configuration for
the current trading cycle.

Persistent configuration remains stored in PostgreSQL.

---

# 15. Complete Runtime Flow

The complete runtime relationship between the session, registries, market
data, strategies, and signal distribution can be represented as:

```text
                         MarketSessionManager
                                  │
                                  │ MARKET_OPEN
                                  ▼
                               EventBus
                                  │
                                  ▼
                           SessionManager
                                  │
                 ┌────────────────┼────────────────┐
                 │                │                │
                 ▼                ▼                ▼
        SubscriptionRegistry  StrategyRegistry  StrategyUserRegistry
                 │                │                │
                 ▼                ▼                ▼
        MarketDataManager   StrategyEngine   SignalDistributor
                 │                │                │
                 ▼                ▼                ▼
          WebSocketClient   StrategyFactory  SignalDelivery
                 │                │
                 ▼                ▼
             Tick Data       Strategy Objects
                                  │
                                  ▼
                         Strategy Signal
                                  │
                                  ▼
                   STRATEGY_SIGNAL_GENERATED
                                  │
                                  └──────────────→ SignalDistributor
```

The three registries therefore form the runtime configuration layer used by
different parts of the trading engine.

---

# 16. Design Decisions

## 16.1 Registry is a Runtime State Store

The registries maintain runtime state.

They do not:

* Create WebSocket connections.
* Subscribe to brokers.
* Access PostgreSQL.
* Create strategy objects.
* Execute strategies.
* Manage user lifecycle.
* Deliver signals.

Each of these responsibilities belongs to another component.

---

## 16.2 EventBus is for Communication

The EventBus is used to communicate events between independent components.

Examples include:

```text
MARKET_OPEN
MARKET_CLOSE
SESSIONS_READY
TICK_RECEIVED
STRATEGY_SIGNAL_GENERATED
```

The EventBus is not used for simple registry reads and writes.

For example:

```text
SubscriptionRegistry.get_symbols()
```

is a direct state lookup and does not require an event.

---

## 16.3 SubscriptionRegistry Represents Market Data Requirements

`SubscriptionRegistry` answers:

> Which symbols does the runtime currently require market data for?

It does not represent individual user subscriptions.

For example:

```text
User 101 → NIFTY
User 202 → NIFTY
```

still produces only:

```text
NIFTY
```

inside `SubscriptionRegistry`.

---

## 16.4 StrategyRegistry Represents Computation Groups

`StrategyRegistry` answers:

> Which unique strategy configurations need to be computed?

Multiple users can therefore share the same strategy computation.

For example:

```text
EMA + NIFTY + 5m
        │
        ├── User 101
        └── User 202
```

requires only one strategy computation group.

---

## 16.5 StrategyUserRegistry Represents User Relationships

`StrategyUserRegistry` answers:

> Which users are subscribed to a particular strategy group?

For example:

```text
EMA + NIFTY + 5m
        │
        ├── 101
        └── 202
```

This relationship is maintained separately from `StrategyRegistry`.

---

## 16.6 Computation and Distribution are Separate

The architecture intentionally separates:

```text
StrategyRegistry
        │
        └── What should be computed?
```

from:

```text
StrategyUserRegistry
        │
        └── Who should receive the result?
```

This allows one strategy computation to produce a signal that can then be
distributed to multiple users.

---

## 16.7 Registries Do Not Access PostgreSQL

The registries contain runtime state only.

Persistent configuration is loaded through the database layer:

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
Runtime Registries
```

The registries themselves do not query the database.

---

## 16.8 Registry State is Rebuilt Per Trading Cycle

Runtime registry state is created when the trading cycle starts and cleared
when the cycle ends.

The persistent database configuration survives application restarts.

Therefore:

```text
PostgreSQL
    │
    │ persistent configuration
    ▼
SessionManager
    │
    │ runtime configuration
    ▼
Registries
```

---

# 17. Testing

The Registry module is covered by unit and integration tests.

---

## SubscriptionRegistry

Tests cover:

* Adding a symbol.
* Adding multiple symbols.
* Duplicate symbol handling.
* Removing a symbol.
* Removing a non-existent symbol.
* Returning a copy of registered symbols.

---

## StrategyRegistry

Tests cover:

* Adding a strategy.
* Adding multiple strategies.
* Duplicate strategy handling.
* Different parameters creating different strategy groups.
* Removing a strategy.
* Removing a non-existent strategy.
* Returning a copy of registered strategies.

---

## StrategyUserRegistry

Tests cover:

* Creating an empty registry.
* Subscribing a user to a strategy group.
* Multiple users subscribing to the same strategy group.
* Preventing duplicate subscriptions.
* Keeping different strategy groups independent.
* Unsubscribing a user.
* Handling an unsubscribe for a non-existent user.
* Removing a strategy group when its last subscriber is removed.
* Clearing all subscriptions.
* Returning a copy of subscribers.

---

## SessionManager Integration

Tests cover:

* `MARKET_OPEN` subscription.
* `MARKET_CLOSE` subscription.
* Populating `SubscriptionRegistry` on market open.
* Populating `StrategyRegistry` on market open.
* Populating `StrategyUserRegistry` on market open.

---

# 18. Current Status

The Registry module currently contains:

```text
registry/
├── subscription_registry.py
├── strategy_registry.py
└── strategy_user_registry.py
```

Current implementation status:

* [x] `SubscriptionRegistry` implemented.
* [x] `StrategyGroup` implemented.
* [x] `StrategyRegistry` implemented.
* [x] `StrategyUserRegistry` implemented.
* [x] SessionManager integrated with `SubscriptionRegistry`.
* [x] SessionManager integrated with `StrategyRegistry`.
* [x] SessionManager integrated with `StrategyUserRegistry`.
* [x] MarketDataManager integrated with `SubscriptionRegistry`.
* [x] StrategyEngine integrated with `StrategyRegistry`.
* [x] SignalDistributor integrated with `StrategyUserRegistry`.
* [x] Unit tests added.
* [x] Integration tests added.
* [x] Full project test suite passing.

---

# 19. Future Work

Potential future improvements include:

* Supporting dynamic runtime subscription changes.
* Supporting user subscription updates without requiring a full trading-cycle
  restart.
* Extending registry state management as additional runtime configuration
  requirements are introduced.
* Improving lifecycle handling when users or strategies change during an
  active trading session.

Any future changes should preserve the separation between persistent
configuration, runtime state, computation, and signal distribution.

---

# Registry Summary

The Registry module provides three separate runtime state stores:

```text
                    Runtime Registry Layer
                             │
          ┌──────────────────┼──────────────────┐
          │                  │                  │
          ▼                  ▼                  ▼
 SubscriptionRegistry  StrategyRegistry  StrategyUserRegistry
          │                  │                  │
          ▼                  ▼                  ▼
       Symbols        Strategy Groups       User IDs
          │                  │                  │
          ▼                  ▼                  ▼
 MarketDataManager     StrategyEngine     SignalDistributor
```

The separation can be summarized as:

```text
SubscriptionRegistry
    → What market data is required?

StrategyRegistry
    → What strategy computations are required?

StrategyUserRegistry
    → Which users are subscribed to those computations?
```

Together, these registries provide the runtime configuration required by the
trading engine while keeping state management separate from market-data
processing, strategy execution, database access, and signal delivery.

