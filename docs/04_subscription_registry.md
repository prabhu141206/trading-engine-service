# Subscription Registry

## Purpose

`SubscriptionRegistry` maintains the **in-memory mapping between users and market symbols**.

It acts as a fast lookup index for future market-data routing and websocket subscription management.

The registry is intentionally kept independent from the database. It receives `UserSession` objects from `SessionManager` and builds runtime indexes.

---

## Responsibilities

* Track which users are subscribed to each symbol.
* Track which symbols belong to each user.
* Maintain symbol reference counts.
* Support fast symbol lookup for market-data delivery.
* Support efficient websocket subscribe/unsubscribe decisions.

---

## What this module does NOT do

* Database queries
* Session lifecycle management
* Market-data handling
* Tick routing
* Strategy execution
* Order management

Those responsibilities belong to other modules.

---

## Dependencies

### Internal dependencies

* `session.user_session`

### External dependencies

* Python `collections.defaultdict`

---

## High-level flow

```text
MARKET_OPEN
    ↓
SessionManager
    ↓
_load_active_users()
    ↓
UserSession objects
    ↓
SubscriptionRegistry.add_session()
    ↓
Build symbol indexes
```

---

## Why this module exists

Without a registry, delivering a tick would require scanning every active user:

```python
for session in all_sessions:
    if symbol in session.subscribed_symbols:
        deliver_tick(session)
```

Complexity: **O(number_of_users)**.

With `SubscriptionRegistry`:

```python
users = registry.get_users(symbol)
```

Complexity: **O(1)** average lookup.

---

# Internal data structures

The registry maintains three indexes.

## Symbol → Users

```python
{
    "NIFTY": {101, 202},
    "BANKNIFTY": {101},
    "FINNIFTY": {303}
}
```

## User → Symbols

```python
{
    101: {"NIFTY", "BANKNIFTY"},
    202: {"NIFTY"},
    303: {"FINNIFTY"}
}
```

## Symbol reference counts

```python
{
    "NIFTY": 2,
    "BANKNIFTY": 1,
    "FINNIFTY": 1
}
```

---

# Integration with SessionManager

## UserSession model

```python
@dataclass
class UserSession:
    user_id: int
    subscribed_symbols: set[str]
```

## Runtime creation

```python
session = UserSession(
    user_id=101,
    subscribed_symbols={"NIFTY", "BANKNIFTY"}
)

registry.add_session(session)
```

The registry updates all internal indexes immediately.

---

# Public API

## Add session

```python
registry.add_session(session)
```

Registers all symbol subscriptions for the user.

---

## Remove session

```python
registry.remove_session(user_id)
```

Removes all subscriptions associated with the user.

---

## Get users for symbol

```python
registry.get_users("NIFTY")
```

Returns:

```python
{101, 202}
```

---

## Get symbols for user

```python
registry.get_symbols(101)
```

Returns:

```python
{"NIFTY", "BANKNIFTY"}
```

---

## Get all active symbols

```python
registry.get_all_symbols()
```

Returns:

```python
{"NIFTY", "BANKNIFTY", "FINNIFTY"}
```

---

## Get symbol reference count

```python
registry.get_symbol_count("NIFTY")
```

Returns:

```python
2
```

---

## Clear registry

```python
registry.clear()
```

Removes all runtime mappings.

---

# Reference count behavior

## Initial state

```text
NIFTY count = 0
```

## User 101 subscribes

```text
NIFTY count = 1
```

## User 202 subscribes

```text
NIFTY count = 2
```

## User 101 removed

```text
NIFTY count = 1
```

## User 202 removed

```text
NIFTY count = 0
```

When the count reaches zero, the symbol is no longer required by any user.

---

# Future websocket integration

`MarketDataManager` will use the registry to synchronize subscriptions.

## Example

### Registry symbols

```python
{"NIFTY", "BANKNIFTY"}
```

### Active websocket symbols

```python
{"NIFTY"}
```

### Actions

* Subscribe: `BANKNIFTY`
* Unsubscribe: none

This avoids duplicate websocket subscriptions.

---

# Market close cleanup

During `MARKET_CLOSE`:

```python
registry.remove_session(user_id)
```

After all users are removed:

```python
registry.get_all_symbols() == set()
```

The registry becomes empty.

---

# Design principles

## Single responsibility

The registry only maintains subscription indexes.

## In-memory only

It is a runtime cache, not a persistence layer.

## Fast lookup

All public lookups are dictionary-based.

## Decoupled from database

Only `SessionManager` interacts with persistent storage.

---

# Typical lifecycle

## Market open

```text
SessionManager loads users
    ↓
Registry populated
    ↓
Symbols become active
```

## Market close

```text
Sessions removed
    ↓
Registry cleaned
    ↓
No active symbols remain
```

---

# Example end-to-end scenario

### Active users

| User | Symbols          |
| ---- | ---------------- |
| 101  | NIFTY, BANKNIFTY |
| 202  | NIFTY            |
| 303  | FINNIFTY         |

### Tick arrives

```python
tick.symbol = "NIFTY"
```

### Lookup

```python
registry.get_users("NIFTY")
```

### Result

```python
{101, 202}
```

Only users 101 and 202 receive the tick.

---

# Testing

Covered behaviors:

* single user registration
* multiple users same symbol
* session removal
* reverse lookup
* all-symbol retrieval
* registry clear
* symbol reference counting

Run tests:

```bash
python -m pytest tests/test_subscription_registry -v
```

---

# Future enhancements

Planned future improvements:

* thread-safe locking
* metrics for active symbols
* subscription change events
* persistence snapshot support
* distributed registry abstraction

These are intentionally excluded from the current implementation.

---

# Summary

`SubscriptionRegistry` is a lightweight runtime index that provides:

* **symbol → users lookup**
* **user → symbols lookup**
* **symbol reference counting**

It forms the bridge between `SessionManager` and the future `MarketDataManager`, enabling efficient shared websocket subscriptions and fast market-data routing in a multi-user trading system.
