# Module 4 — Registry

## 1. Objective

The Registry module maintains runtime configuration required by the
trading engine.

It contains two registries:

- `SubscriptionRegistry`
- `StrategyRegistry`

The registries store runtime state required by other components but do
not perform external operations such as WebSocket connections or
strategy execution.

---

## 2. Responsibilities

### SubscriptionRegistry

Responsible for:

- Registering required market symbols.
- Maintaining unique symbols.
- Removing symbols.
- Providing registered symbols to `MarketDataManager`.
- Clearing runtime subscription state.

### StrategyRegistry

Responsible for:

- Registering unique strategy configurations.
- Preventing duplicate strategy groups.
- Removing strategy configurations.
- Providing strategy configurations to `StrategyEngine`.
- Clearing runtime strategy state.

---

# 3. Architecture

```text
                         SessionManager
                              │
                 ┌────────────┴────────────┐
                 │                         │
                 ▼                         ▼
       SubscriptionRegistry        StrategyRegistry
                 │                         │
                 ▼                         ▼
        MarketDataManager           StrategyEngine
                 │                         │
                 ▼                         ▼
          WebSocketClient          StrategyFactory
```

---

# 4. SubscriptionRegistry

## Purpose

`SubscriptionRegistry` maintains the unique symbols required by the
active runtime sessions.

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

---

## 4.1 API

```python
add_symbol(symbol)
remove_symbol(symbol)
get_symbols()
clear()
```

### `add_symbol()`

Registers a symbol.

```python
registry.add_symbol("NIFTY")
```

### `remove_symbol()`

Removes a symbol.

```python
registry.remove_symbol("NIFTY")
```

### `get_symbols()`

Returns all currently registered symbols.

```python
symbols = registry.get_symbols()
```

A copy is returned so callers cannot directly modify the internal
registry state.

### `clear()`

Removes all registered symbols.

This is used when the market session ends.

---

# 5. StrategyRegistry

## Purpose

`StrategyRegistry` maintains the unique strategy configurations
required by the trading engine.

Example:

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

---

# 6. StrategyGroup

`StrategyGroup` represents the identity of one strategy configuration.

Example:

```python
StrategyGroup(
    strategy_type="EMA",
    symbol="NIFTY",
    timeframe="5m",
    parameters=(("period", 10),)
)
```

Fields:

| Field | Description |
|---|---|
| `strategy_type` | Strategy type |
| `symbol` | Symbol used by the strategy |
| `timeframe` | Strategy timeframe |
| `parameters` | Strategy-specific parameters |

`StrategyGroup` is immutable using `frozen=True`.

This allows strategy configurations to be stored safely in a `set`.

---

# 7. StrategyRegistry API

```python
add_strategy(group)
remove_strategy(group)
get_strategies()
clear()
```

### `add_strategy()`

Registers a strategy configuration.

Duplicate configurations are automatically ignored.

### `remove_strategy()`

Removes a strategy configuration.

### `get_strategies()`

Returns all unique strategy groups.

A copy is returned to protect the internal registry state.

### `clear()`

Removes all registered strategy groups.

---

# 8. SessionManager Integration

`SessionManager` is responsible for populating both registries when the
market opens.

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
                ▼
         StrategyRegistry
```

For every `UserSession`:

```python
for symbol in session.subscribed_symbols:
    subscription_registry.add_symbol(symbol)

for strategy in session.strategies:
    strategy_registry.add_strategy(strategy)
```

---

# 9. MarketDataManager Integration

`MarketDataManager` reads the required symbols from
`SubscriptionRegistry`.

The registry does not directly communicate with `MarketDataManager`
through the `EventBus`.

The flow is:

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

The EventBus is used for lifecycle notification:

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

---

# 10. StrategyEngine Integration

`StrategyEngine` will read the unique strategy configurations from
`StrategyRegistry`.

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

---

# 11. Market Close

When the market closes, `SessionManager` clears the runtime state.

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
     └── clear StrategyRegistry
```

This ensures that the registries represent only the current market
runtime.

---

# 12. Complete Runtime Flow

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
                 ┌────────┴────────┐
                 │                 │
                 ▼                 ▼
        SubscriptionRegistry   StrategyRegistry
                 │                 │
                 ▼                 ▼
        MarketDataManager     StrategyEngine
                 │                 │
                 ▼                 ▼
          WebSocketClient     StrategyFactory
                 │
                 ▼
             Tick Data
                 │
                 ▼
          TICK_RECEIVED
```

---

# 13. Design Decisions

## Registry is a State Store

The registries maintain runtime state.

They do not:

- Create WebSocket connections.
- Subscribe to brokers.
- Create strategy objects.
- Execute strategies.
- Manage user lifecycle.
- Publish market-data events.

---

## EventBus is for Communication

The EventBus is used to communicate events between independent
components.

Examples:

```text
MARKET_OPEN
MARKET_CLOSE
SESSIONS_READY
TICK_RECEIVED
```

The EventBus is not used for simple registry reads and writes.

---

## Dependency Direction

```text
SessionManager
    │
    ├── writes → SubscriptionRegistry
    └── writes → StrategyRegistry

MarketDataManager
    │
    └── reads → SubscriptionRegistry

StrategyEngine
    │
    └── reads → StrategyRegistry
```

This keeps responsibilities separated.

---

# 14. Testing

## SubscriptionRegistry

Tests cover:

- Adding a symbol.
- Adding multiple symbols.
- Duplicate symbol handling.
- Removing a symbol.
- Removing a non-existent symbol.
- Returning a copy of registered symbols.

## StrategyRegistry

Tests cover:

- Adding a strategy.
- Adding multiple strategies.
- Duplicate strategy handling.
- Different parameters creating different groups.
- Removing a strategy.
- Removing a non-existent strategy.
- Returning a copy of registered strategies.

## SessionManager Integration

Tests cover:

- `MARKET_OPEN` subscription.
- `MARKET_CLOSE` subscription.
- Populating `SubscriptionRegistry` on market open.
- Populating `StrategyRegistry` on market open.

---

# 15. Current Status

- [x] SubscriptionRegistry implemented
- [x] StrategyGroup implemented
- [x] StrategyRegistry implemented
- [x] SessionManager integrated with SubscriptionRegistry
- [x] SessionManager integrated with StrategyRegistry
- [x] MarketDataManager integrated with SubscriptionRegistry
- [x] Unit tests added
- [x] Integration tests added
- [x] Full test suite passing

---

# 16. Future Work

The Registry module will later support the following components:

```text
SubscriptionRegistry
        │
        ▼
MarketDataManager
        │
        ▼
Tick Distribution
```

and:

```text
StrategyRegistry
        │
        ▼
StrategyEngine
        │
        ▼
StrategyFactory
        │
        ▼
Strategy Runtime
```

Future work will also address dynamic user/session changes while the
market is running.