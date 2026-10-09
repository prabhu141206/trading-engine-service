
# Integration Testing

## 1. Goal

The goal of integration testing is to prove that the real production components of the trading engine work correctly when connected together.

Unit tests prove that individual components behave correctly in isolation.

Integration tests prove that those components can communicate through the real `EventBus`, pass the correct data to each other, respect the expected event order, and complete the intended market-data pipeline.

The primary integration flow is:

```text
Fake WebSocket
      ↓
MarketDataManager
      ↓
TICK_RECEIVED
      ↓
CandleBuilder
      ↓
CANDLE_BATCH_CLOSED
      ↓
IndicatorEngine
      ↓
INDICATOR_BATCH_UPDATED
      ↓
StrategyEngine
      ↓
STRATEGY_SIGNAL_GENERATED
      ↓
SignalDistributor
      ↓
SignalDelivery
```

The integration tests should use the actual production components wherever possible.

The purpose is not to create another version of the production system for testing.

The purpose is to surround the existing production system with controlled external inputs and verify that the real components work together.

---

## 2. Why Integration Testing?

Unit tests are important, but they cannot prove that the entire system works correctly when components are connected.

For example, individual tests can prove:

- `CandleBuilder` can create a candle.
- `IndicatorEngine` can calculate EMA.
- `StrategyEngine` can execute a strategy.
- `SignalDistributor` can distribute a signal.

However, those tests do not necessarily prove:

```text
Tick
 ↓
CandleBuilder
 ↓
CandleBatch
 ↓
IndicatorEngine
 ↓
IndicatorBatch
 ↓
StrategyEngine
 ↓
StrategyOutput
 ↓
SignalDistributor
```

works correctly as one system.

Integration testing is therefore used to verify:

- EventBus communication
- Event subscription
- Event publishing
- Data flow between components
- Correct event ordering
- Real component interaction
- Runtime lifecycle
- Startup behavior
- Shutdown behavior
- Strategy execution through the real pipeline

### Important principle

> Testing code should surround the production system rather than change the production system for testing.

We should avoid adding testing-only branches, special production behavior, or temporary production wiring just to make an integration test easier.

---

# 3. Production Pipeline

The main integration pipeline is:

```text
                         EXTERNAL INPUT
                              │
                              ▼
                     ┌─────────────────┐
                     │ Fake WebSocket  │
                     └────────┬────────┘
                              │
                              ▼
                     ┌─────────────────┐
                     │ MarketData      │
                     │ Manager         │
                     └────────┬────────┘
                              │
                         TICK_RECEIVED
                              │
                              ▼
                     ┌─────────────────┐
                     │ CandleBuilder   │
                     └────────┬────────┘
                              │
                     CANDLE_BATCH_CLOSED
                              │
                              ▼
                     ┌─────────────────┐
                     │ IndicatorEngine │
                     └────────┬────────┘
                              │
                  INDICATOR_BATCH_UPDATED
                              │
                              ▼
                     ┌─────────────────┐
                     │ StrategyEngine  │
                     └────────┬────────┘
                              │
                 STRATEGY_SIGNAL_GENERATED
                              │
                              ▼
                     ┌─────────────────┐
                     │SignalDistributor│
                     └────────┬────────┘
                              │
                              ▼
                       SignalDelivery
```

The `EventBus` connects the components.

Components should not directly call the next component when the architecture specifies an event-based connection.

For example:

```text
CandleBuilder
     │
     └── publishes CANDLE_BATCH_CLOSED
                    │
                    ▼
             EventBus
                    │
                    ▼
             IndicatorEngine
```

---

# 4. What Is Real vs Fake?

The integration test should fake only external dependencies that we need to control.

## 4.1 Fake Components

### Fake WebSocket

The real market-data WebSocket is not used during integration testing.

Instead, a fake WebSocket provides deterministic ticks.

This allows us to control:

- Symbol
- Price
- Timestamp
- Tick sequence
- Number of ticks
- Market-day simulation

Example:

```text
Fake WebSocket
      ↓
Tick 1
Tick 2
Tick 3
...
Tick N
```

The test can simulate an entire market session without waiting for real time.

---

### Fake Historical Data Provider

`IndicatorEngine` requires historical candles to warm up the indicator state.

The integration test should provide deterministic historical candles.

Example:

```text
Historical candles
       ↓
IndicatorEngine warm-up
       ↓
EMA state ready
```

The purpose is not to test the historical data provider itself.

The purpose is to provide the data required by the real `IndicatorEngine`.

---

### Fake Session / Configuration Data

The integration environment may provide controlled session/configuration data required to create the runtime environment.

This allows the test to define:

- Active users
- Symbols
- Strategies
- Strategy groups
- Required runtime configuration

Again, this data exists only to prepare the production pipeline.

---

# 4.2 Real Components

The following components should remain real during integration testing.

### EventBus

The real `EventBus` is used.

This is important because we want to verify actual event communication.

---

### MarketDataManager

The real `MarketDataManager` is used.

Only its external WebSocket dependency is replaced with the fake WebSocket.

---

### CandleBuilder

The real `CandleBuilder` is used.

Ticks from the fake WebSocket should travel through the real candle-building logic.

---

### IndicatorEngine

The real `IndicatorEngine` is used.

It should:

1. Warm up its indicator state.
2. Receive `CANDLE_BATCH_CLOSED`.
3. Update EMA.
4. Publish `INDICATOR_BATCH_UPDATED`.

---

### StrategyEngine

The real `StrategyEngine` is used.

It should:

1. Receive candle/indicator events.
2. Correlate the data.
3. Create completed strategy contexts.
4. Dispatch them to the registered strategy.
5. Receive strategy outputs.
6. Publish `STRATEGY_SIGNAL_GENERATED`.

---

### Strategy

The real strategy implementation is used.

The integration test should exercise the actual strategy logic rather than replacing it with a mock.

---

### SignalDistributor

The real `SignalDistributor` is used.

It should receive:

```text
STRATEGY_SIGNAL_GENERATED
```

and determine which users are subscribed to that strategy group.

---

# 5. Test Lifecycle

Every integration test should follow a predictable lifecycle.

```text
SETUP
  ↓
START
  ↓
FEED DATA
  ↓
PROCESS
  ↓
ASSERT
  ↓
SHUTDOWN
```

## 5.1 SETUP

Create the integration environment.

This includes:

- EventBus
- Registries
- Fake external dependencies
- Real production components
- Strategy configuration
- Test users/subscriptions
- Historical indicator data
- Event observers required for assertions

The objective is to create the same production relationships without connecting to real external services.

---

## 5.2 START

Start the production components in the correct lifecycle order.

The test must ensure that the required event subscriptions exist before market data is injected.

The integration environment should reach a state where:

```text
Production components
        ↓
Ready
```

before ticks are sent.

---

## 5.3 FEED DATA

The fake WebSocket provides deterministic ticks.

For example:

```text
10:15:01
10:15:20
10:16:10
10:17:30
...
10:19:59
```

The timestamps can represent market time even though the test itself executes much faster than real time.

This allows the test to simulate a market session without waiting five minutes for every candle.

---

## 5.4 PROCESS

The production system processes the data normally.

The expected chain is:

```text
Tick
 ↓
MarketDataManager
 ↓
TICK_RECEIVED
 ↓
CandleBuilder
 ↓
CANDLE_BATCH_CLOSED
 ↓
IndicatorEngine
 ↓
INDICATOR_BATCH_UPDATED
 ↓
StrategyEngine
 ↓
STRATEGY_SIGNAL_GENERATED
 ↓
SignalDistributor
```

No testing-only shortcut should bypass these production components.

---

## 5.5 ASSERT

The test should verify observable system behavior.

Examples:

### Market data

```text
Ticks were received.
```

### Candle pipeline

```text
Expected candle was created.
```

### Indicator pipeline

```text
Expected indicator batch was generated.
```

### Strategy pipeline

```text
Expected strategy output was generated.
```

### Signal distribution

```text
Expected subscribed users received the signal.
```

The test should focus on meaningful outputs rather than internal implementation details whenever possible.

---

## 5.6 SHUTDOWN

The integration environment must shut down cleanly.

The test should verify that:

- Market-data processing stops.
- Background processing stops.
- Runtime state is cleaned.
- No background thread remains running.
- The test does not affect another test.

Integration tests must leave the environment clean.

---

# 6. Test Scenarios

Integration testing will be built incrementally.

We should not create one enormous test that attempts to test everything at once.

---

## Scenario 1 — Tick to Candle

### Goal

Prove that market ticks can travel through the real market-data and candle pipeline.

```text
Fake WebSocket
      ↓
MarketDataManager
      ↓
TICK_RECEIVED
      ↓
CandleBuilder
      ↓
CANDLE_BATCH_CLOSED
```

### Verify

- Fake ticks are accepted.
- `TICK_RECEIVED` is published.
- CandleBuilder receives the ticks.
- Correct candles are created.
- Candle batch is published.

This scenario isolates the first part of the complete pipeline.

### Status

**PASSED**

### Test Result

```text
pytest tests/integration/test_market_pipeline.py -v

1 passed in 0.74s
```

### Result

The real market-data-to-candle pipeline is working correctly.

The integration test successfully verified that ticks emitted by the fake WebSocket travel through the real `MarketDataManager`, are published as `TICK_RECEIVED` events, processed by the real `CandleBuilder`, and finalized into a `CANDLE_BATCH_CLOSED` event.

The test also verified the resulting NIFTY candle's:

- Open
- High
- Low
- Close
- Timeframe
- Start time
- End time

---


## Scenario 2 — Candle to Indicator

### Goal

Prove that the candle pipeline connects correctly to the indicator pipeline.

```text
CandleBuilder
      ↓
CANDLE_BATCH_CLOSED
      ↓
IndicatorEngine
      ↓
INDICATOR_BATCH_UPDATED
```

### Verify

- Indicator state is ready.
- Candle batch reaches IndicatorEngine.
- EMA is updated.
- Indicator batch is published.
- IndicatorEngine receives `SESSIONS_READY`.
- Historical candles are used for indicator warm-up.
- EMA 10 state becomes ready.
- `CANDLE_BATCH_CLOSED` is received.
- EMA 10 is updated from the completed candle.
- Updated indicator state is stored.
- `INDICATOR_BATCH_UPDATED` is published.
- The indicator batch contains the expected symbol and timeframe.

### Status

**PASSED**

### Test Result

```text
pytest tests/integration/test_market_pipeline.py -v

2 passed in 0.31s
```

### Result

The real candle-to-indicator pipeline is working correctly.

The integration test verified that the real `IndicatorEngine` can warm up its EMA state using controlled historical data, receive a completed candle batch through the real `EventBus`, update the EMA state, and publish an `INDICATOR_BATCH_UPDATED` event.

---

## Scenario 3 — Candle + Indicator to Strategy

### Goal

Prove that the real candle and indicator events reach StrategyEngine and are correlated correctly.

```text
CANDLE_BATCH_CLOSED
          +
INDICATOR_BATCH_UPDATED
          ↓
StrategyCorrelator
          ↓
StrategyEngine
          ↓
Strategy
          ↓
STRATEGY_SIGNAL_GENERATED
```

### Verify

- Candle data reaches the correlator.
- Indicator data reaches the correlator.
- The two datasets are matched.
- A StrategyContext is produced.
- The real strategy receives the context.
- Expected StrategyOutput is generated.

### Result

**Status:** PASSED ✅

The integration test confirmed that the real event-driven strategy pipeline works correctly.

- `CANDLE_BATCH_CLOSED` reached `StrategyEngine`.
- `INDICATOR_BATCH_UPDATED` reached `StrategyEngine`.
- `StrategyCorrelator` matched the candle and indicator using the same symbol, timeframe, and interval.
- A `StrategyContext` was produced only after both inputs were available.
- The real `EMAStrategy` received the context and armed its trigger.
- A subsequent `TICK_RECEIVED` event broke the trigger candle high.
- The real strategy generated the expected `BUY ENTRY` output.
- `STRATEGY_SIGNAL_GENERATED` was published through the real `EventBus`.

**Test result:**

```text
1 passed, 2 deselected in 0.24s
---

## Scenario 4 — Strategy Signal Distribution

### Goal

Prove that a real strategy signal reaches the signal-distribution layer.

```text
STRATEGY_SIGNAL_GENERATED
          ↓
SignalDistributor
          ↓
StrategyUserRegistry
          ↓
SignalDelivery
```

### Verify

- SignalDistributor receives the strategy signal.
- Correct subscribers are identified.
- Subscribed users receive the signal.
- Users subscribed to another strategy do not receive it.

### Result

**Status:** PASSED ✅

The integration test confirmed that a generated strategy signal is correctly distributed to all users subscribed to the corresponding `StrategyGroup`.

- `STRATEGY_SIGNAL_GENERATED` entered the real `SignalDistributor` through the `EventBus`.
- `SignalDistributor` published one `SIGNAL_RECEIVED` event for the generated signal.
- `StrategyUserRegistry` correctly identified the subscribed users.
- The signal was delivered to users `101`, `202`, and `303`.
- User `404`, who was subscribed to a different `StrategyGroup`, did not receive the signal.
- The same `StrategyOutput` was delivered to every matching subscriber.
- One `SIGNAL_DISTRIBUTED` event was generated for each successful delivery.

**Test result:**

```text
1 passed, 3 deselected in 0.30s
```

---


## Scenario 5 — Complete Market Pipeline

After the previous scenarios are working independently, combine them:

```text
Fake WebSocket
      ↓
MarketDataManager
      ↓
CandleBuilder
      ↓
IndicatorEngine
      ↓
StrategyEngine
      ↓
SignalDistributor
      ↓
SignalDelivery
```

### Goal

Prove that the complete production pipeline works from market data to user signal delivery.

This becomes the primary end-to-end integration test.

### Result

**Status:** PASSED ✅

The complete market pipeline was successfully verified using the real production components.

- Market ticks entered through the `FakeWebSocketClient`.
- `MarketDataManager` converted incoming ticks into `TICK_RECEIVED` events.
- `CandleBuilder` consumed the tick events and produced a completed 5-minute candle.
- `IndicatorEngine` warmed up from controlled historical data and processed the completed candle.
- `IndicatorEngine` published the resulting `INDICATOR_BATCH_UPDATED` event.
- `StrategyEngine` correlated the candle and indicator data.
- The real EMA strategy received the resulting context and armed its trigger.
- A subsequent breakout tick generated the expected `BUY ENTRY` signal.
- `SignalDistributor` received the generated strategy signal.
- The signal was delivered to the subscribed user through the `SignalDelivery` abstraction.

**Test result:**

```text
1 passed, 4 deselected in 0.29s
```

---

## Scenario 6 — Multiple Symbols

### Goal

Verify that the pipeline correctly handles multiple symbols.

Example:

```text
NIFTY
BANKNIFTY
RELIANCE
```

The system should maintain independent candle and indicator state for each symbol.

### Result

**Status:** PASSED ✅

The integration test confirmed that multiple symbols can flow through the same market-processing pipeline while maintaining independent symbol state and strategy routing.

- `NIFTY` and `BANKNIFTY` were registered as active market-data symbols.
- The real `MarketDataManager` accepted ticks for both symbols.
- `CandleBuilder` maintained separate candle data for each symbol.
- `IndicatorEngine` warmed up and maintained independent indicator state for both symbols.
- `StrategyEngine` created and routed the corresponding EMA strategy instances independently.
- The NIFTY strategy generated a signal associated with the NIFTY `StrategyGroup`.
- The BANKNIFTY strategy generated a signal associated with the BANKNIFTY `StrategyGroup`.
- The NIFTY signal was delivered only to the NIFTY subscriber.
- The BANKNIFTY signal was delivered only to the BANKNIFTY subscriber.
- No cross-symbol routing occurred.

**Test result:**

```text
1 passed, 5 deselected in 0.23s
```

---

## Scenario 7 — Multiple Strategy Subscribers

### Goal

Verify signal fan-out.

Example:

```text
EMA/NIFTY/5m
       ↓
Signal
       ↓
 ┌─────┼─────┐
 ↓     ↓     ↓
User1 User2 User3
```

One strategy computation should produce one strategy signal.

The signal distributor then distributes that signal to all relevant users.

### Result

PASSED.

The test verified that one strategy signal can be distributed to multiple users subscribed to the same StrategyGroup.

The flow was:

```text
One StrategyOutput
       ↓
STRATEGY_SIGNAL_GENERATED
       ↓
SignalDistributor
   ┌───┼───┐
   ↓   ↓   ↓
User101 User202 User303

```

---

# 7. Problems Found

This section records problems discovered during integration testing.

Do not immediately modify production code when a test fails.

First determine:

1. Where did the event stop?
2. Which component received it?
3. Which component should have received it next?
4. Was the event payload correct?
5. Was the component actually subscribed?
6. Was the component ready?
7. Is the problem in production logic or in the test setup?

Example:

```text
Problem:
IndicatorEngine did not process the first live candle.

Investigation:
Indicator state had not completed warm-up.

Cause:
The integration test injected live data before the indicator runtime was ready.

Resolution:
Wait for the real warm-up lifecycle to complete before feeding live ticks.

Production code changed:
No.
```

This section should be updated only with actual problems discovered during testing.

Do not record assumptions as problems.

---

# 8. Decisions

This section records architectural and testing decisions made during integration work.

## Decision 1 — Use real production components

Integration tests should use real production components wherever possible.

Reason:

```text
The purpose is to test component interaction,
not recreate the production architecture inside tests.
```

---

## Decision 2 — Fake only external dependencies

External market-data and historical-data sources can be replaced with deterministic fakes.

Reason:

```text
External services are unpredictable and unnecessary
for deterministic integration testing.
```

---

## Decision 3 — Use the real EventBus

The integration pipeline must use the real EventBus.

Reason:

```text
Event subscription and event delivery are part
of the architecture being tested.
```

---

## Decision 4 — Do not modify production code only for tests

Testing should not introduce special production branches merely to make integration testing easier.

Reason:

```text
The test should validate the production architecture,
not a testing-specific version of it.
```

---

## Decision 5 — Simulate market time

Ticks may contain timestamps representing real market intervals while executing immediately.

Reason:

```text
The system should process market-time data without
requiring the test to wait for real-world time to pass.
```

---

## Decision 6 — Build integration tests incrementally

Do not immediately create one huge end-to-end test.

Build:

```text
Tick → Candle
        ↓
Candle → Indicator
        ↓
Indicator + Candle → Strategy
        ↓
Strategy → Signal Distribution
        ↓
Complete Pipeline
```

Reason:

```text
When a complete pipeline fails, smaller integration tests
make it easier to identify exactly where the failure occurred.
```

---

# 9. Final Result

This section will be completed after integration testing is finished.

The final result should document:

### Tests

```text
Integration tests:
7 passed
0 failed
```

### Pipeline

```text
Fake WebSocket
      ↓
MarketDataManager       ✓
      ↓
CandleBuilder           ✓
      ↓
IndicatorEngine         ✓
      ↓
StrategyEngine          ✓
      ↓
SignalDistributor       ✓
      ↓
SignalDelivery          ✓
```

### Runtime lifecycle

```text
Startup                 ✓
Market processing       ✓
Signal generation       ✓
Signal distribution     ✓
Shutdown                ✓
Cleanup                 ✓
```

### Production changes

Document whether production code was changed during integration testing.

The preferred result is:

```text
Production architecture changes:
None
```

if the integration tests can validate the existing architecture without testing-specific modifications.

---
