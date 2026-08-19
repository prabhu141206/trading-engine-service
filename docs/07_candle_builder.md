# 07 — Candle Builder

> Converts incoming market ticks into time-based OHLC candles and publishes completed candles as `CandleBatch` events.

---

## 1. Why Candle Builder Exists

The Market Data layer receives market data as individual ticks.

For example:

```text
10:15:01  NIFTY       25100
10:15:04  NIFTY       25102
10:15:10  BANKNIFTY   55200
10:16:02  NIFTY       25098
10:17:15  NIFTY       25110
10:19:52  NIFTY       25105
```

A trading strategy normally does not want to calculate a 5-minute candle from these ticks itself.

It needs:

```text
NIFTY
10:15 → 10:20

Open  = 25100
High  = 25110
Low   = 25098
Close = 25105
```

Therefore, the Candle Builder is responsible for transforming:

```text
Tick Stream
    ↓
Time-based OHLC Candle
```

The current implementation builds:

```text
5-minute candles
```

---

## 2. Where Candle Builder Fits

The Candle Builder sits between the Market Data system and future Indicator/Strategy systems.

```text
                         Market Data
                              |
                              v
                     MarketDataManager
                              |
                              |
                       TICK_RECEIVED
                              |
                              v
                          EventBus
                              |
                              v
                       CandleBuilder
                              |
                              |
                       Current Candles
                              |
                              |
                       CandleScheduler
                              |
                         Time Boundary
                              |
                              v
                    finalize_interval()
                              |
                              v
                         CandleBatch
                              |
                              |
                    CANDLE_BATCH_CLOSED
                              |
                              v
                          EventBus
                              |
                              v
                     Indicator Engine
                              |
                              v
                      Strategy Engine
```

The important architectural separation is:

```text
MarketDataManager
    → receives market data

CandleBuilder
    → builds candles

CandleScheduler
    → determines when a candle interval ends

IndicatorEngine
    → calculates indicators

StrategyEngine
    → makes trading decisions
```

No component should take responsibility for another component's job.

---

## 3. Problem With Direct Tick-to-Strategy Processing

Suppose the strategy requires a 5-minute candle.

The Market Data system might receive thousands of ticks during those five minutes.

If the Strategy Engine directly consumes all ticks, it would need to:

1. Determine the candle interval.
2. Track the first price.
3. Track the highest price.
4. Track the lowest price.
5. Track the latest price.
6. Detect when the interval ends.
7. Decide when the candle is complete.
8. Repeat this for every symbol.

That would mix:

```text
Market Data
+
Time Management
+
Candle Construction
+
Strategy Logic
```

This is poor separation of responsibility.

Instead:

```text
Market Data
    ↓
Tick
    ↓
Candle Builder
    ↓
Completed Candle
    ↓
Strategy / Indicator
```

The downstream components receive structured data instead of rebuilding it.

---

## 4. Current Candle Engine Design

The Candle Engine contains two important components:

* `CandleBuilder`
* `CandleScheduler`

They have different responsibilities.

### CandleBuilder

The CandleBuilder answers:

> What is the current candle?

It handles:

```text
Tick
 ↓
Bucket
 ↓
Create/Update Candle
 ↓
Finalize Candle
 ↓
CandleBatch
```

### CandleScheduler

The scheduler answers:

> When is the candle interval complete?

It handles:

```text
Clock
 ↓
Next Boundary
 ↓
Boundary Reached
 ↓
Call CandleBuilder
```

Therefore:

```text
CandleBuilder ≠ CandleScheduler
```

This separation is intentional.

---

## 5. Folder Structure

Current Candle module:

```text
src/
│
├── candle/
│   ├── candle_builder.py
│   ├── candle_models.py
│   ├── candle_scheduler.py
│   └── candle_timeframe.py
│
├── event_system/
│   ├── event.py
│   ├── event_bus.py
│   └── event_type.py
│
└── market_data/
    └── models.py
```

Tests:

```text
tests/
│
└── test_candle/
    ├── test_candle_builder.py
    ├── test_candle_scheduler.py
    └── test_candle_integration.py
```

---

## 6. Files and Their Responsibilities

### `candle_builder.py`

Contains the `CandleBuilder`.

Responsible for:

* receiving ticks
* determining the candle bucket
* creating candles
* updating OHLC
* maintaining active candles
* finalizing intervals
* creating `CandleBatch`
* publishing `CANDLE_BATCH_CLOSED`

### `candle_models.py`

Contains:

```text
Candle
CandleBatch
```

These are data models.

They do not control the candle-building process.

### `candle_timeframe.py`

Contains the timeframe definition.

Current supported timeframe:

```text
FIVE_MINUTES
```

### `candle_scheduler.py`

Responsible for:

* calculating interval boundaries
* waiting for boundaries
* triggering the callback
* starting/stopping the scheduler

It does not construct candles.

---

## 7. Dependencies

`CandleBuilder` depends on:

```python
from event_system.event import Event
from event_system.event_bus import EventBus
from event_system.event_type import EventType

from market_data.models import Tick

from candle.candle_models import Candle, CandleBatch
from candle.candle_timeframe import CandleTimeframe
```

The dependency relationships are:

```text
CandleBuilder
    |
    +── EventBus
    +── Event
    +── EventType
    +── Tick
    +── Candle
    +── CandleBatch
    +── CandleTimeframe
```

The `EventBus` is injected into the `CandleBuilder`.

```python
CandleBuilder(event_bus)
```

The `CandleBuilder` does not create its own `EventBus`.

This is dependency injection.

---

## 8. Event Dependencies

The Candle Builder participates in two event flows.

### Incoming

Event:

```text
TICK_RECEIVED
```

Payload:

```text
Tick
```

Flow:

```text
MarketDataManager
        ↓
TICK_RECEIVED
        ↓
EventBus
        ↓
CandleBuilder
```

### Outgoing

Event:

```text
CANDLE_BATCH_CLOSED
```

Payload:

```text
CandleBatch
```

Flow:

```text
CandleBuilder
        ↓
CANDLE_BATCH_CLOSED
        ↓
EventBus
        ↓
Future consumers
```

---

## 9. Candle Model

A Candle represents one symbol for one timeframe and one interval.

Conceptually:

```python
Candle(
    symbol="NIFTY",
    timeframe="5m",
    start_time=...,
    end_time=...,
    open=25100,
    high=25110,
    low=25098,
    close=25105,
)
```

The important fields are:

```text
symbol
timeframe
start_time
end_time
open
high
low
close
```

---

## 10. Candle OHLC Rules

For every candle:

```text
Open
    = first tick price in the interval

High
    = highest tick price in the interval

Low
    = lowest tick price in the interval

Close
    = latest tick price in the interval
```

Example:

Ticks:

```text
100
105
98
103
```

Candle:

```text
Open  = 100
High  = 105
Low   = 98
Close = 103
```

---

## 11. CandleBatch

A `CandleBatch` represents all finalized candles belonging to one interval.

Example:

```python
CandleBatch(
    timeframe="5m",
    start_time=10:15,
    end_time=10:20,
    candles={
        "NIFTY": Candle(...),
        "BANKNIFTY": Candle(...),
        "RELIANCE": Candle(...),
    },
)
```

The structure is:

```text
CandleBatch
│
├── timeframe
├── start_time
├── end_time
│
└── candles
      ├── NIFTY
      ├── BANKNIFTY
      ├── RELIANCE
      └── ...
```

---

## 12. Why CandleBatch Instead of Individual Candle Events

Assume 1,000 symbols have candles completed at the same boundary.

An inefficient design would publish:

```text
CANDLE_CLOSED → NIFTY
CANDLE_CLOSED → BANKNIFTY
CANDLE_CLOSED → RELIANCE
...
```

Potentially thousands of events.

The current design publishes:

```text
CANDLE_BATCH_CLOSED
```

once:

```text
CandleBatch
                        |
        +---------------+---------------+
        |               |               |
      NIFTY         BANKNIFTY       RELIANCE
        |               |               |
        +---------------+---------------+
                        |
                        v
                     EventBus
```

This gives downstream consumers one coherent interval-level payload.

---

## 13. Internal State

The CandleBuilder maintains:

```python
self._current_candles
```

with type:

```python
dict[
    tuple[str, CandleTimeframe],
    Candle,
]
```

The key is:

```text
(symbol, timeframe)
```

Example:

```text
_current_candles

("NIFTY", FIVE_MINUTES)
    → Candle(10:15 → 10:20)

("BANKNIFTY", FIVE_MINUTES)
    → Candle(10:15 → 10:20)

("RELIANCE", FIVE_MINUTES)
    → Candle(10:15 → 10:20)
```

---

## 14. Why the Key Contains Symbol and Timeframe

A candle belongs to both:

```text
Symbol
+
Timeframe
```

Therefore:

```text
("NIFTY", FIVE_MINUTES)
```

is different from:

```text
("NIFTY", FIFTEEN_MINUTES)
```

and:

```text
("BANKNIFTY", FIVE_MINUTES)
```

is different from:

```text
("NIFTY", FIVE_MINUTES)
```

This allows the state model to support multiple symbols and eventually multiple timeframes.

The current implementation only actively processes the 5-minute timeframe, but the state structure does not hard-code the symbol.

---

## 15. CandleBuilder Lifecycle

The CandleBuilder lifecycle is:

```text
Create
  ↓
start()
  ↓
Subscribe to TICK_RECEIVED
  ↓
Receive ticks
  ↓
Build/update candles
  ↓
Finalize intervals
  ↓
Publish CandleBatch
```

The important lifecycle method is:

```python
start()
```

It performs:

```python
self._event_bus.subscribe(
    EventType.TICK_RECEIVED,
    self._on_tick,
)
```

After this subscription, the EventBus can deliver tick events to the CandleBuilder.

---

## 16. Tick Event Entry Point

The CandleBuilder receives events through:

```python
_on_tick(event)
```

Conceptually:

```python
def _on_tick(self, event):
    tick = event.payload
    self._process_tick(tick)
```

The flow is:

```text
EventBus
   ↓
_on_tick()
   ↓
event.payload
   ↓
Tick
   ↓
_process_tick()
```

The event itself is not the candle data.

The event contains a `Tick` as its payload.

---

## 17. Tick Processing

`_process_tick()` performs the actual candle-building logic.

The process is:

```text
Tick
 |
 v
Get timeframe
 |
 v
Build key
 |
 v
Calculate bucket start
 |
 v
Calculate bucket end
 |
 v
Find current candle
 |
 +---------------------------+
 |                           |
 v                           v
No candle                 Candle exists
 |                           |
 v                           v
Create candle             Compare bucket
                             |
                  +----------+----------+
                  |                     |
                Same                  New
                  |                     |
                  v                     v
             Update OHLC          Create new candle
```

---

## 18. Current Timeframe

The current implementation explicitly uses:

```text
timeframe = CandleTimeframe.FIVE_MINUTES
```

Therefore every incoming tick currently becomes part of a 5-minute candle.

Future timeframe support should be introduced deliberately rather than duplicating CandleBuilder logic.

---

## 19. Building the State Key

For a tick:

```text
symbol = NIFTY
```

and:

```text
timeframe = FIVE_MINUTES
```

the key becomes:

```python
key = ("NIFTY", CandleTimeframe.FIVE_MINUTES)
```

This key is used to locate the active candle.

---

## 20. Time Bucket Calculation

The CandleBuilder determines which 5-minute interval contains a tick.

For example:

```text
10:15:01 → 10:15
10:16:20 → 10:15
10:17:50 → 10:15
10:19:59 → 10:15

10:20:00 → 10:20
10:20:01 → 10:20
10:24:59 → 10:20
```

The calculation is:

```python
minute = (timestamp.minute // 5) * 5
```

Then:

```python
timestamp.replace(
    minute=minute,
    second=0,
    microsecond=0,
)
```

Therefore:

```text
10:17:42
```

becomes:

```text
10:15:00
```

and belongs to:

```text
10:15 → 10:20
```

---

## 21. First Tick for a Symbol

Suppose the first NIFTY tick arrives:

```text
10:15:01
price = 100
```

There is no current candle.

Therefore:

```text
current_candle = None
```

The builder creates:

```text
NIFTY
10:15 → 10:20

Open  = 100
High  = 100
Low   = 100
Close = 100
```

It stores that candle in:

```text
_current_candles
```

The tick itself does **not** publish a completed candle.

It only starts the candle.

---

## 22. Updating an Existing Candle

Suppose the next tick arrives:

```text
10:16:10
price = 105
```

Its bucket is still:

```text
10:15
```

Therefore:

```text
current_candle.start_time == start_time
```

The builder updates:

```text
High = max(100, 105) = 105
Low  = min(100, 105) = 100
Close = 105
```

Open remains:

```text
100
```

Result:

```text
Open  = 100
High  = 105
Low   = 100
Close = 105
```

---

## 23. Another Tick

Suppose:

```text
10:17:30
price = 98
```

The candle becomes:

```text
Open  = 100
High  = 105
Low   = 98
Close = 98
```

Then:

```text
10:19:50
price = 103
```

Final state before completion:

```text
Open  = 100
High  = 105
Low   = 98
Close = 103
```

---

## 24. Important: Tick Arrival Does Not Publish the Candle

This is a key design decision.

When a tick arrives at:

```text
10:19:50
```

the candle is almost complete, but it is not yet finalized.

The CandleBuilder only updates:

```text
_current_candles
```

It does not publish:

```text
CANDLE_BATCH_CLOSED
```

The candle is finalized only when the interval boundary is reached.

---

## 25. Why Candle Completion Depends on Time

Consider:

```text
10:15 → 10:20
```

Suppose the last tick arrives at:

```text
10:19:30
```

Then no tick arrives until:

```text
10:20:10
```

The candle still ended at:

```text
10:20:00
```

It cannot wait for the next tick to determine completion.

Therefore:

```text
Tick arrival
    ≠
Time boundary
```

This is exactly why the CandleScheduler exists.

---

## 26. CandleScheduler

The CandleScheduler tracks the time boundaries.

For a 5-minute timeframe:

```text
10:15
10:20
10:25
10:30
10:35
...
```

The scheduler determines when the next boundary occurs.

When the boundary is reached, it calls the configured callback.

---

## 27. Scheduler-to-Builder Connection

The scheduler is constructed with:

```python
on_boundary=candle_builder.finalize_interval
```

Conceptually:

```text
CandleScheduler
       |
       | on_boundary
       v
CandleBuilder.finalize_interval
```

Therefore the scheduler does not need to know the internal structure of the CandleBuilder.

It only knows:

> When the interval ends, call this callback.

---

## 28. What Happens at 10:20

Assume the active candle is:

```text
NIFTY
10:15 → 10:20

O = 100
H = 105
L = 98
C = 103
```

At:

```text
10:20
```

the scheduler reaches the boundary.

The flow becomes:

```text
10:20 boundary
      ↓
CandleScheduler
      ↓
on_boundary(interval_start)
      ↓
CandleBuilder.finalize_interval(10:15)
```

The CandleBuilder now knows:

> The 10:15 → 10:20 interval is complete.

---

## 29. finalize_interval()

The public method:

```python
def finalize_interval(
    self,
    interval_start: datetime,
) -> None:
    self._finalize_interval(interval_start)
```

exists as the connection point between the scheduler and builder.

The scheduler calls:

```text
finalize_interval()
```

The builder performs the actual finalization internally.

---

## 30. Why the Operation Was Renamed From Flush

The earlier implementation used the term:

```text
flush
```

This caused conceptual confusion because "flush" sounds like:

```text
delete
erase
clear
```

But that is not the actual operation.

The operation is:

```text
FINALIZE
```

because the builder:

1. Finds completed candles.
2. Collects them.
3. Creates a batch.
4. Publishes the batch.
5. Removes those completed candles from active state.

So:

```text
Finalize
    ≠
Delete
```

The completed candle has already been converted into a `CandleBatch` and published.

---

## 31. Finding Completed Candles

Suppose:

```text
interval_start = 10:15
interval_end   = 10:20
```

The builder iterates over:

```text
_current_candles
```

and selects candles where:

```text
candle.start_time == interval_start
```

and:

```text
candle.end_time == interval_end
```

For example:

```text
_current_candles

NIFTY
10:15 → 10:20   ← select

BANKNIFTY
10:15 → 10:20   ← select

RELIANCE
10:20 → 10:25   ← do not select
```

The result becomes:

```text
completed_candles = {
    "NIFTY": ...,
    "BANKNIFTY": ...,
}
```

---

## 32. Why Not Publish One Symbol at a Time?

Suppose:

```text
NIFTY
BANKNIFTY
RELIANCE
```

all completed at the same boundary.

The system does not do:

```text
publish NIFTY
publish BANKNIFTY
publish RELIANCE
```

Instead:

```text
completed_candles
        ↓
CandleBatch
        ↓
one EventBus publish
```

This is important because the downstream Indicator Engine can treat the batch as:

> The completed candle snapshot for this interval.

---

## 33. Creating CandleBatch

After collecting:

```text
completed_candles
```

the builder creates:

```python
batch = CandleBatch(
    timeframe=timeframe.value,
    start_time=interval_start,
    end_time=interval_end,
    candles=completed_candles,
)
```

Example:

```text
CandleBatch

timeframe  = "5m"
start_time = 10:15
end_time   = 10:20

candles:
    NIFTY
    BANKNIFTY
    RELIANCE
```

---

## 34. Publishing the Batch

The builder then publishes:

```python
self._event_bus.publish(
    Event(
        event_type=EventType.CANDLE_BATCH_CLOSED,
        payload=batch,
    )
)
```

This is the actual point where the completed candle data enters the EventBus.

The full connection is:

```text
Scheduler
    ↓
finalize_interval()
    ↓
_find completed candles
    ↓
CandleBatch
    ↓
Event(...)
    ↓
EventBus.publish()
    ↓
CANDLE_BATCH_CLOSED
```

---

## 35. Before the Publish Call

Before:

```python
self._event_bus.publish(...)
```

the completed candles are only local runtime data.

They exist inside:

```text
completed_candles
```

Then:

```text
CandleBatch
```

is created.

Then:

```text
Event
```

is created.

Only after:

```text
_event_bus.publish(...)
```

does the event enter the event system.

This distinction is important.

---

## 36. What Happens After Publishing

After the batch is published, the finalized candle keys are removed from:

```text
_current_candles
```

Why?

Because `_current_candles` means:

> Candles that are currently being formed.

Once the candle is completed:

```text
Current Candle
      ↓
CandleBatch
      ↓
EventBus
```

It is no longer an active candle.

---

## 37. What Happens to the Next Tick

After 10:20, suppose:

```text
10:20:01
NIFTY = 110
```

Bucket calculation gives:

```text
10:20
```

The old:

```text
10:15 → 10:20
```

candle is no longer active.

Therefore the builder creates:

```text
NIFTY
10:20 → 10:25

Open  = 110
High  = 110
Low   = 110
Close = 110
```

The next cycle has started.

---

## 38. Complete State Transition

The candle state transition is:

```text
First Tick
                      |
                      v
               CREATE CANDLE
                      |
                      v
             CURRENT / ACTIVE
                      |
                More Ticks
                      |
                      v
                UPDATE OHLC
                      |
                Time Boundary
                      |
                      v
                  FINALIZE
                      |
                      v
                CandleBatch
                      |
                      v
                   EventBus
                      |
                      v
                  COMPLETED

Next Tick
    |
    v
New Candle
```

---

## 39. Complete 5-Minute Example

Consider:

```text
Interval:
10:15:00 → 10:20:00
```

Ticks:

```text
10:15:01 NIFTY 100
10:16:05 NIFTY 105
10:17:10 NIFTY 98
10:18:20 NIFTY 102
10:19:50 NIFTY 103
```

After each tick:

```text
First tick:
O=100 H=100 L=100 C=100

105:
O=100 H=105 L=100 C=105

98:
O=100 H=105 L=98 C=98

102:
O=100 H=105 L=98 C=102

103:
O=100 H=105 L=98 C=103
```

At 10:20:

```text
Scheduler
    ↓
finalize_interval(10:15)
```

Creates:

```text
CandleBatch(
    timeframe="5m",
    start_time=10:15,
    end_time=10:20,
    candles={
        "NIFTY": Candle(
            O=100,
            H=105,
            L=98,
            C=103
        )
    }
)
```

Then:

```text
CANDLE_BATCH_CLOSED
```

is published.

---

## 40. Multiple Symbols at the Same Boundary

Suppose the active state contains:

```text
NIFTY
10:15 → 10:20

BANKNIFTY
10:15 → 10:20

RELIANCE
10:15 → 10:20
```

At 10:20:

```text
Scheduler
    ↓
finalize_interval(10:15)
```

The builder creates:

```text
CandleBatch
│
├── NIFTY
├── BANKNIFTY
└── RELIANCE
```

Then publishes exactly one:

```text
CANDLE_BATCH_CLOSED
```

event for that batch.

---

## 41. Symbols With No Candle

A batch contains candles that actually exist for that interval.

Suppose:

```text
NIFTY
10:15 → 10:20

BANKNIFTY
10:20 → 10:25
```

At 10:20, only NIFTY belongs to the completed interval.

Therefore:

```text
CandleBatch
    |
    └── NIFTY
```

BANKNIFTY is not included in that completed batch because its active candle belongs to the next interval.

---

## 42. Empty Interval

If there are no candles for an interval:

```text
10:15 → 10:20
```

then:

```text
completed_candles = {}
```

No batch is published.

Therefore:

```text
No candles
    ↓
No CandleBatch
    ↓
No CANDLE_BATCH_CLOSED event
```

This prevents meaningless empty events.

---

## 43. Important Boundary Rule

The system uses half-open interval semantics conceptually:

```text
[start_time, end_time)
```

For:

```text
10:15 → 10:20
```

ticks belong as:

```text
10:15:00 <= tick < 10:20:00
```

Therefore:

```text
10:19:59.999
```

belongs to:

```text
10:15 → 10:20
```

while:

```text
10:20:00.000
```

belongs to:

```text
10:20 → 10:25
```

This prevents a tick at the exact boundary from belonging to two candles.

---

## 44. Why Scheduler Is Required Even When Ticks Have Timestamps

A common question is:

> If ticks have timestamps, why not finalize the candle when the next tick arrives?

Because the market may stop sending ticks temporarily.

Example:

```text
10:19:59
last tick

10:20:00
interval ends

10:20:01
no tick

10:20:02
no tick

10:20:30
next tick
```

The 10:15–10:20 candle was already complete at 10:20.

Therefore candle completion must be based on time, not on arrival of the next tick.

---

## 45. Why CandleBuilder Does Not Own the Clock

If CandleBuilder also controlled the clock, it would have two responsibilities:

```text
Build candles
+
Schedule time
```

Instead:

```text
CandleBuilder
    → data transformation

CandleScheduler
    → time management
```

This makes both components simpler.

---

## 46. Testing Strategy

The Candle module is tested at multiple levels.

```text
Tests
               |
       +-------+-------+
       |               |
       v               v
 CandleBuilder    CandleScheduler
       |               |
       +-------+-------+
               |
               v
        Integration Tests
```

The tests verify both individual behavior and the connection between components.

---

## 47. CandleBuilder Tests

### `test_create_first_candle`

Verifies:

```text
First tick
    ↓
Candle created
```

and:

```text
Open = price
High = price
Low = price
Close = price
```

### `test_update_candle_ohlc`

Verifies:

```text
Existing candle
      ↓
New tick
      ↓
OHLC updated
```

Specifically:

```text
High = max(previous high, price)
Low  = min(previous low, price)
Close = price
```

Open remains unchanged.

### `test_multiple_symbols_have_independent_candles`

Verifies:

```text
NIFTY state
≠
BANKNIFTY state
```

Updating one symbol must not affect another.

### `test_new_interval_creates_new_candle`

Verifies:

```text
10:15 interval
      ↓
10:20 boundary
      ↓
10:20 interval
```

creates a new candle.

---

## 48. Finalization Tests

### `test_flush_interval_creates_one_candle_batch`

Historical test name may still use `flush`, but the current conceptual operation is `finalize`.

Verifies:

```text
Completed candles
      ↓
One CandleBatch
      ↓
CANDLE_BATCH_CLOSED
```

### `test_flush_removes_completed_candles`

Verifies that completed candles are removed from:

```text
_current_candles
```

after finalization.

### `test_tick_after_boundary_belongs_to_new_interval`

Verifies that a tick after the boundary is assigned to the next interval.

### `test_flush_empty_interval_does_not_publish`

Verifies:

```text
No completed candle
      ↓
No CandleBatch
      ↓
No EventBus publication
```

---

## 49. Scheduler Tests

The scheduler tests verify:

### `test_next_five_minute_boundary`

Example:

```text
10:17
```

should produce:

```text
10:20
```

### `test_boundary_when_already_at_exact_boundary`

Verifies behavior when the current time is already exactly on a boundary.

### `test_boundary_crossing_hour`

Example:

```text
10:55
```

must correctly produce:

```text
11:00
```

### `test_get_interval_start`

Example:

```text
10:17:42
```

must map to:

```text
10:15:00
```

### `test_boundary_triggers_callback`

Verifies:

```text
Boundary
   ↓
Callback invoked
```

The callback is the connection to:

```text
CandleBuilder.finalize_interval
```

---

## 50. Integration Tests

The integration tests verify the actual relationship between components.

The important flow is:

```text
Tick
 ↓
CandleBuilder
 ↓
Current Candle
 ↓
Scheduler Boundary
 ↓
Finalize
 ↓
CandleBatch
 ↓
EventBus
```

The tests ensure that the individual components are not only correct independently but also correctly connected.

---

## 51. Test Command

Run Candle tests:

```bash
pytest tests/test_candle -v
```

Run the entire project:

```bash
pytest -v
```

Current Candle test suite:

```text
18 tests passing
```

---

## 52. Fake WebSocket for Runtime Testing

The current development system uses a Fake WebSocket.

The abstraction is:

```text
WebSocketClient
```

which is a `Protocol`.

The fake implementation provides:

```text
FakeWebSocketClient
```

for simulation.

The architecture becomes:

```text
FakeWebSocketClient
        ↓
MarketDataManager
        ↓
TICK_RECEIVED
        ↓
EventBus
        ↓
CandleBuilder
```

This allows the candle pipeline to be tested without connecting to a real broker.

---

## 53. Important Distinction: Protocol vs Implementation

`WebSocketClient` is not instantiated directly.

It is an interface/contract:

```python
class WebSocketClient(Protocol):
    ...
```

Therefore this is invalid:

```python
WebSocketClient()
```

The application uses a concrete implementation such as:

```python
FakeWebSocketClient()
```

for the current demo.

This is unrelated to CandleBuilder itself but is part of the runtime dependency chain that supplies ticks to it.

---

## 54. Main Application Wiring

The composition root connects the components.

Conceptually:

```python
event_bus = EventBus()

candle_builder = CandleBuilder(
    event_bus=event_bus,
)

candle_scheduler = CandleScheduler(
    CandleTimeframe.FIVE_MINUTES,
    candle_builder.finalize_interval,
)

candle_builder.start()
candle_scheduler.start()
```

The most important connection is:

```python
candle_builder.finalize_interval
```

being passed to:

```text
CandleScheduler
```

as the boundary callback.

---

## 55. Complete Dependency Direction

The dependency direction is:

```text
main.py
   |
   +------------------------+
   |                        |
   v                        v
EventBus              CandleBuilder
                           |
                           v
                    CandleScheduler
```

Runtime event direction:

```text
MarketDataManager
        |
        v
     EventBus
        |
        v
 CandleBuilder
        |
        v
 CandleBatch
        |
        v
     EventBus
        |
        v
 IndicatorEngine
```

The EventBus provides loose coupling between producers and consumers.

---

## 56. What Happens Internally During One Complete Interval

Assume:

```text
10:15 → 10:20
```

### Step 1 — Tick arrives

```text
10:15:01 NIFTY 100
```

### Step 2 — EventBus delivers it

```text
TICK_RECEIVED
    ↓
CandleBuilder._on_tick()
```

### Step 3 — Builder calculates bucket

```text
10:15:01
    ↓
10:15:00
```

### Step 4 — Builder creates candle

```text
NIFTY 10:15→10:20
O=100 H=100 L=100 C=100
```

### Step 5 — More ticks arrive

The builder updates:

```text
High
Low
Close
```

### Step 6 — 10:20 arrives

Scheduler detects the boundary.

### Step 7 — Scheduler calls builder

```text
finalize_interval(10:15)
```

### Step 8 — Builder finds completed candles

```text
NIFTY
BANKNIFTY
...
```

### Step 9 — Builder creates CandleBatch

```text
CandleBatch(
    10:15 → 10:20,
    candles={...}
)
```

### Step 10 — Builder publishes

```text
CANDLE_BATCH_CLOSED
```

### Step 11 — EventBus distributes it

Future consumers can subscribe.

### Step 12 — Completed candles are removed from active state

The next interval can now begin.

---

## 57. What Is Actually Stored in Memory?

During the interval:

```text
_current_candles
```

contains only the currently forming candles.

Example at 10:17:

```text
_current_candles:

NIFTY
    → 10:15-10:20 candle

BANKNIFTY
    → 10:15-10:20 candle
```

At 10:20:

```text
CandleBatch
    → contains finalized 10:15-10:20 candles
```

Then:

```text
_current_candles
```

no longer contains those completed candles.

After the next NIFTY tick:

```text
_current_candles:

NIFTY
    → 10:20-10:25 candle
```

This means the active dictionary does not become an unlimited historical candle store.

---

## 58. Historical Data vs Active State

The CandleBuilder currently manages:

```text
ACTIVE CANDLES
```

not:

```text
ALL HISTORICAL CANDLES
```

This distinction is important.

The active state answers:

> What candle is currently being built?

The CandleBatch answers:

> What candle just completed?

If historical storage is required later, it should be implemented as a separate persistence/history component.

---

## 59. Why CandleBatch Is the Boundary Between Modules

Before the batch:

```text
High-frequency tick processing
```

After the batch:

```text
Completed time-based market data
```

Therefore:

```text
Tick World
                        |
                        v
                 CandleBuilder
                        |
                        |
                CANDLE_BATCH_CLOSED
                        |
                        v
                   Candle World
                        |
                        v
                Indicator / Strategy
```

This makes `CandleBatch` an important architectural boundary.

---

## 60. Future Indicator Engine Integration

The next module can subscribe to:

```text
CANDLE_BATCH_CLOSED
```

Example:

```text
EventBus
   |
   +----> IndicatorEngine
```

The Indicator Engine receives:

```text
CandleBatch
```

and can calculate:

```text
EMA
VWAP
RSI
Volume indicators
```

The CandleBuilder should not perform these calculations.

---

## 61. Future Strategy Integration

The eventual pipeline becomes:

```text
Market Tick
      |
      v
MarketDataManager
      |
      v
EventBus
      |
      v
CandleBuilder
      |
      v
CandleBatch
      |
      v
IndicatorEngine
      |
      v
IndicatorResult
      |
      v
StrategyEngine
      |
      v
Signal
```

This allows each component to evolve independently.

---

## 62. Current Scope

The Candle Builder currently handles:

```text
[YES]

✓ Tick consumption
✓ 5-minute bucketing
✓ Candle creation
✓ OHLC updates
✓ Multiple symbols
✓ Interval finalization
✓ CandleBatch creation
✓ EventBus publication
✓ Scheduler integration
✓ Boundary handling
✓ Unit tests
✓ Integration tests
✓ Fake market-data testing
```

It intentionally does not handle:

```text
[NO]

✗ Indicators
✗ Strategy
✗ Orders
✗ Positions
✗ P&L
✗ Broker connection
✗ Historical persistence
✗ User-specific candle state
```

---

## 63. Important Design Decisions

### Decision 1 — Event-driven tick input

Instead of CandleBuilder directly calling MarketDataManager:

```text
MarketDataManager
       ↓
EventBus
       ↓
CandleBuilder
```

This keeps the components loosely coupled.

### Decision 2 — Dictionary keyed by `(symbol, timeframe)`

Instead of:

```text
one CandleBuilder per symbol
```

the system uses:

```text
one CandleBuilder
        |
        +-- symbol/timeframe state
```

This scales better architecturally.

### Decision 3 — Scheduler controls time

The CandleBuilder does not independently sleep or wait for boundaries.

The Scheduler owns time.

### Decision 4 — Batch publication

Completed candles are grouped into:

```text
CandleBatch
```

and published as one event.

### Decision 5 — Finalization instead of deletion

The interval is finalized first:

```text
collect
→ batch
→ publish
→ remove active state
```

This preserves the meaning of the operation.

### Decision 6 — No one-second candle

The raw tick stream already exists.

A separate one-second candle layer is unnecessary for the current architecture.

---

## 64. Failure Scenarios Considered

### No Tick for a Symbol

No candle is created for that symbol.

No artificial candle is generated by CandleBuilder.

### Empty Interval

No completed candles means:

```text
No CandleBatch
```

is published.

### Tick Exactly at Boundary

A tick at:

```text
10:20:00
```

belongs to:

```text
10:20 → 10:25
```

not:

```text
10:15 → 10:20
```

### Tick Immediately Before Boundary

A tick at:

```text
10:19:59
```

belongs to:

```text
10:15 → 10:20
```

### Multiple Symbols

Each symbol has independent state.

### New Interval

The old candle is finalized separately, and the new tick starts the next candle.

---

## 65. Performance Characteristics

For every incoming tick, the builder performs approximately:

1. Determine timeframe.
2. Create dictionary key.
3. Calculate bucket.
4. Dictionary lookup.
5. Create or update candle.

The active candle lookup is dictionary-based.

Conceptually:

```text
O(1)
```

for locating the current candle by:

```text
(symbol, timeframe)
```

Interval finalization currently iterates through the active candle dictionary to identify candles belonging to the requested interval.

Therefore finalization is proportional to the number of active candle entries.

This is acceptable for the current design and can be optimized later if profiling demonstrates a real bottleneck.

---

## 66. Concurrency Considerations

`_current_candles` is mutable shared state.

Therefore the runtime must ensure controlled access if tick processing and interval finalization can execute concurrently.

Current design assumes the EventBus/scheduler execution model provides controlled access.

If the architecture later introduces:

```text
multiple tick-processing threads
parallel symbol workers
async event consumers
```

then this state-management boundary must be revisited.

Do not introduce locks without a demonstrated concurrency requirement.

---

## 67. Why We Do Not Store Every Tick Inside Candle

The CandleBuilder does not need to retain every tick after updating OHLC.

For a standard OHLC candle, only:

```text
Open
High
Low
Close
```

are required to represent the completed candle.

Therefore:

```text
Tick
 ↓
Update OHLC
 ↓
Tick no longer required by CandleBuilder
```

This keeps the active candle state small.

If tick-level historical storage is required, that belongs to another component.

---

## 68. Data Ownership

The ownership model is:

```text
MarketDataManager
    owns/reports tick stream

CandleBuilder
    owns currently forming candle state

CandleBatch
    represents finalized candle data

IndicatorEngine
    future owner of indicator state
```

The CandleBuilder should not become a global repository for all market history.

---

## 69. CandleBuilder as a State Transformer

Conceptually, CandleBuilder performs:

```text
State + Tick
      ↓
New State
```

Example:

Previous State:

```text
NIFTY
O=100
H=105
L=98
C=100
```

Incoming Tick:

```text
103
```

New State:

```text
NIFTY
O=100
H=105
L=98
C=103
```

At the interval boundary:

```text
State
  ↓
Finalize
  ↓
Output CandleBatch
  ↓
Remove finalized state
```

This is the central mental model for understanding the component.

---

## 70. Final Architecture

The complete Candle subsystem is:

```text
+-------------------+
| MarketDataManager |
+---------+---------+
          |
          | Tick
          v
   +-------------+
   |   EventBus  |
   +------+------+
          |
   TICK_RECEIVED
          |
          v
  +----------------+
  | CandleBuilder  |
  +-------+--------+
          |
          |
  _current_candles
          |
          |
  +-------v--------+
  | CandleScheduler|
  +-------+--------+
          |
    time boundary
          |
          v
 finalize_interval()
          |
          v
    CandleBatch
          |
          |
 CANDLE_BATCH_CLOSED
          |
          v
       EventBus
          |
          v
   Indicator Engine
          |
          v
    Strategy Engine
```

---

## 71. One-Line Mental Model

The entire Candle Builder can be remembered as:

```text
Ticks → Build Current Candle → Time Boundary → Finalize → CandleBatch → EventBus
```

Or, more precisely:

```text
MarketDataManager
        ↓
TICK_RECEIVED
        ↓
CandleBuilder
        ↓
_current_candles
        ↓
CandleScheduler detects boundary
        ↓
finalize_interval()
        ↓
CandleBatch
        ↓
CANDLE_BATCH_CLOSED
        ↓
EventBus
```

---

## 72. Final Responsibility

The Candle Builder's responsibility is:

> Convert a continuous stream of market ticks into correctly time-bucketed OHLC candles, finalize those candles at deterministic timeframe boundaries, group the completed candles into a `CandleBatch`, and publish the batch through the EventBus for downstream processing.

It is deliberately unaware of:

```text
Indicators
Strategies
Orders
Positions
P&L
Broker implementation
```

That separation is what allows the Candle Builder to remain a focused and independently testable component.
