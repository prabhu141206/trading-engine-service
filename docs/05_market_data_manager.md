Good. Stop discussing future million-user scaling for a moment. Let’s design only the current MarketDataManager properly, with clean responsibilities and no unnecessary complexity.

We will design it as if we are writing the first production-quality version.

MarketDataManager Design (Current Phase)

# MarketDataManager Design (Current Phase)

## Goal

The MarketDataManager is responsible for:

* Managing the websocket connection to the broker/market feed.

* Subscribing to required symbols.

* Receiving live ticks.

* Publishing `TICK_RECEIVED` events to EventBus.

It is **not** responsible for:

* Candle creation.

* Indicator calculation.

* Strategy logic.

* User state management.

* Order placement.

---

# Final Responsibility

```
Exchange/Broker WebSocket
          ↓
MarketDataManager
          ↓ publish TICK_RECEIVED
EventBus
```

The manager acts as a **market data gateway**.

---

# Dependencies

```
MarketDataManager(
    event_bus: EventBus,
    subscription_registry: SubscriptionRegistry,
    websocket_client: WebSocketClient
)
```

## Why each dependency exists

### EventBus

Publishes market events.

### SubscriptionRegistry

Provides the list of symbols currently required by the system.

### WebSocketClient

Actual broker websocket implementation.

---

# Public API

```
class MarketDataManager:

    def start(self) -> None
    def stop(self) -> None
```

Only two lifecycle methods are needed for now.

---

# Internal State

```
self._connected: bool = False
self._subscribed_symbols: set[str] = set()
```

## Meaning

* `_connected` → websocket connection status.

* `_subscribed_symbols` → symbols already subscribed at broker side.

---

# Startup Flow

## 1. System publishes `SESSIONS_READY`

SessionManager has already:

* created user sessions,

* updated SubscriptionRegistry.

## 2. MarketDataManager receives event

```
_on_sessions_ready(event)
```

## 3. Connect websocket

```
_websocket_client.connect()
```

## 4. Register tick callback

```
_websocket_client.set_tick_handler(self._on_tick)
```

## 5. Synchronize subscriptions

```
required = registry.get_all_symbols()
websocket.subscribe(required)
```

After this, live ticks begin flowing.

---

# Tick Processing Flow

```
Broker Tick
    ↓
WebSocketClient
    ↓ callback
MarketDataManager._on_tick()
    ↓
EventBus.publish(TICK_RECEIVED)
```

MarketDataManager does **no business logic** on the tick.

---

# Event Published

```
Event(
    event_type=EventType.TICK_RECEIVED,
    payload=tick
)
```

Payload is the immutable Tick object.

---

# Current Subscribers

```
TICK_RECEIVED
   ├── TickCache
   └── CandleBuilder
```

No other subscribers are required in the current phase.

---

# Sync Subscription Algorithm

```
required = registry.get_all_symbols()

to_add = required - _subscribed_symbols
to_remove = _subscribed_symbols - required

if to_add:
    websocket.subscribe(to_add)

if to_remove:
    websocket.unsubscribe(to_remove)

_subscribed_symbols = required
```

This allows future dynamic subscription updates without reconnecting.

---

# Market Close Flow

When `MARKET_CLOSE` is received:

```
websocket.unsubscribe(all_symbols)
websocket.disconnect()
_connected = False
_subscribed_symbols.clear()
```

This keeps the connection lifecycle aligned with market hours.

---

# Error Handling (Current Phase)

### Tick callback exception

Catch and log; never crash websocket thread.

### Subscribe failure

Log and retry later (future enhancement).

### Disconnect

Mark `_connected = False`.

Automatic reconnect can be added later.

---

# Threading Model

Assume websocket callbacks arrive on a websocket thread.

EventBus publish must therefore be thread-safe or used from a single producer thread.

For the current phase, keep it simple and document the assumption.

---

# Pseudocode

```
class MarketDataManager:

    def __init__(self, event_bus, registry, websocket):
        self._event_bus = event_bus
        self._registry = registry
        self._websocket = websocket

        self._connected = False
        self._subscribed_symbols = set()

    def start(self):
        self._event_bus.subscribe(
            EventType.SESSIONS_READY,
            self._on_sessions_ready
        )

        self._event_bus.subscribe(
            EventType.MARKET_CLOSE,
            self._on_market_close
        )

    def _on_sessions_ready(self, event):
        self._connect()
        self._sync_subscriptions()

    def _connect(self):
        if self._connected:
            return

        self._websocket.set_tick_handler(self._on_tick)
        self._websocket.connect()

        self._connected = True

    def _sync_subscriptions(self):
        required = self._registry.get_all_symbols()

        to_add = required - self._subscribed_symbols

        if to_add:
            self._websocket.subscribe(to_add)

        self._subscribed_symbols.update(to_add)

    def _on_tick(self, tick):
        self._event_bus.publish(
            Event(
                event_type=EventType.TICK_RECEIVED,
                payload=tick
            )
        )

    def _on_market_close(self, event):
        if not self._connected:
            return

        if self._subscribed_symbols:
            self._websocket.unsubscribe(self._subscribed_symbols)

        self._websocket.disconnect()

        self._connected = False
        self._subscribed_symbols.clear()
```

---

# Why This Design Is Correct

## Single responsibility

Only market-data connection management.

## Event-driven

No direct calls to TickCache or CandleBuilder.

## Extensible

New tick consumers can subscribe without modifying MarketDataManager.

## Testable

WebSocketClient can be fully mocked.

## Future-ready

Dynamic subscriptions and reconnect logic can be added without changing public API.

---

# Final Architecture Snapshot

```
MarketSessionManager
        ↓ MARKET_OPEN
SessionManager
        ↓ populate registry
        ↓ SESSIONS_READY
MarketDataManager
        ↓ TICK_RECEIVED
EventBus
   ├── TickCache
   └── CandleBuilder
```

This is the version I would freeze before writing code.
