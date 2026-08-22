# TickCache Design (Module 5)

## Objective

Provide a lightweight in-memory cache that always holds the **latest tick per symbol**.

The cache is intended for:

* latest price lookup,
* mark-to-market calculations,
* stop-loss / target checks,
* UI price display,
* reconnect recovery,
* debugging and monitoring.

It is **not** intended for historical storage, candle building, or strategy execution.

---

# Single Responsibility

**TickCache answers exactly one question:**

> *What is the most recent tick for symbol X right now?*

If a component needs historical ticks, candles, indicators, or signals, it should use another module.

---

# Architecture Position

```text
WebSocket
    ↓
MarketDataManager
    ↓ publish TICK_RECEIVED
EventBus
    ├── TickCache
    └── CandleBuilder
```

TickCache is a passive subscriber.

---

# Internal Data Structure

```python
_latest_ticks: dict[str, Tick]
```

Example:

```python
{
    "NIFTY": Tick(...),
    "BANKNIFTY": Tick(...)
}
```

Only one tick per symbol is stored.

When a new tick arrives, the old value is replaced.

---

# Public API

```python
class TickCache:

    def start(self) -> None
    def get_latest(self, symbol: str) -> Tick | None
    def has_symbol(self, symbol: str) -> bool
    def clear(self) -> None
```

---

# Lifecycle

## start()

Registers the cache as a subscriber to `TICK_RECEIVED`.

```python
event_bus.subscribe(
    EventType.TICK_RECEIVED,
    self._on_tick
)
```

---

# Tick Update Flow

```text
TICK_RECEIVED
    ↓
TickCache._on_tick()
    ↓
_latest_ticks[symbol] = tick
```

No additional event is published.

---

# Why No `TICK_CACHE_UPDATED` Event?

The tick event has already been published by MarketDataManager.

Publishing another event would:

* duplicate the same information,
* increase event traffic,
* create unnecessary coupling.

TickCache is storage only.

---

# Read Path

Example:

```python
tick = tick_cache.get_latest("NIFTY")

if tick:
    print(tick.price)
```

This operation should be O(1).

---

# Thread Safety

MarketDataManager may publish ticks from a websocket thread while other threads read the cache.

Therefore protect `_latest_ticks` with a lock.

```python
from threading import Lock

self._lock = Lock()
```

* Writes occur inside the lock.
* Reads also occur inside the lock.

---

# Market Close Behavior

TickCache does not need to react to `MARKET_CLOSE`.

Keeping the last known tick after market close is often useful for:

* end-of-day reporting,
* UI display,
* debugging.

A manual `clear()` method is sufficient.

---

# Failure Behavior

* Invalid tick → ignore or log.
* Exception during update → log and continue.
* Cache must never crash the event pipeline.

---

# Performance Characteristics

| Operation     | Complexity |
| ------------- | ---------- |
| Tick update   | O(1)       |
| Latest lookup | O(1)       |
| Has symbol    | O(1)       |
| Clear         | O(n)       |

Memory usage is proportional to the number of subscribed symbols, not the number of ticks.

---

# Example Timeline

### Tick 1

```text
NIFTY 25100 @ 09:15:01
```

Cache:

```python
{"NIFTY": 25100}
```

### Tick 2

```text
NIFTY 25105 @ 09:15:02
```

Cache:

```python
{"NIFTY": 25105}
```

The previous tick is discarded.

---

# Unit Tests Required

## Test 1 — Update latest tick

* publish one tick,
* verify cache contains it.

## Test 2 — Replace existing tick

* publish tick A,
* publish tick B,
* verify latest tick is B.

## Test 3 — Unknown symbol

* query missing symbol,
* expect `None`.

## Test 4 — Clear cache

* add ticks,
* call `clear()`,
* verify cache is empty.

## Test 5 — Has symbol

* verify True/False behavior.

---

# Module Structure

```text
src/
└── tick_cache/
    ├── __init__.py
    └── tick_cache.py

tests/
└── test_tick_cache/
    └── test_tick_cache.py
```

---

# Documentation

Create:

```text
docs/05_tick_cache.md
```

Include:

* responsibility,
* event flow,
* API,
* thread safety,
* examples,
* test coverage.

---

# Design Decisions Frozen

* Latest tick only.
* No historical storage.
* No event publishing.
* Subscribe only to `TICK_RECEIVED`.
* Thread-safe dictionary.
* Keep last tick after market close.
* O(1) lookup API.

This design is now frozen and can be implemented without further architectural changes.
