# Trading Engine Service — Backend Architecture

## 1. Overview

The Trading Engine Service is a Python-based, event-driven backend designed to support multi-user algorithmic trading workflows.

The current architecture focuses on reliable market-data processing, strategy routing, signal distribution, session lifecycle management, and runtime cleanup.

The system is organized into independent components that communicate through an EventBus. This reduces direct coupling between components and allows different parts of the pipeline to respond to events independently.

### Current milestone

**Status:** Completed

**Git branch:** `integration-testing`

**Latest commit:** `198a0c6` — Improve event failure tracking and shutdown retry safety

**Automated tests:** 224 passed, 0 failed

This milestone establishes a tested backend architecture and reliability baseline. It does not, by itself, establish production readiness for live trading.

---

## 2. Architectural Objectives

The current architecture was developed to support:

- Event-driven communication between backend components.
- Market-data processing through a sequence of pipeline stages.
- Multi-user session and subscription management.
- Strategy grouping and routing.
- Distribution of strategy signals to relevant subscribers.
- Controlled market-close handling and runtime cleanup.
- Subscriber failure recording and logging.
- Safe retry of failed candle finalization.
- Automated testing of individual components and integrated workflows.

The emphasis of this phase is backend infrastructure and lifecycle reliability, rather than profitability or live-trading performance.

---

## 3. High-Level Architecture

The primary processing flow is:

```text
Market Session / Market Data
             |
             v
       MarketDataManager
             |
             v
           EventBus
             |
             v
        Candle Builder
             |
             v
      Candle Batch Events
             |
             v
       Indicator Engine
             |
             v
      Indicator Batch Events
             |
             v
     Strategy Correlator
             |
             v
     Strategy Dispatcher
             |
             v
       Strategy Runtime
             |
             v
       Strategy Signals
             |
             v
     Signal Distributor
             |
             v
     Relevant Subscribers
```

This diagram represents the logical processing flow. Individual components communicate through events, and some stages may be triggered independently by their own event subscriptions.

Monitoring components can observe selected events to track system activity.

---

## 4. Core Components

### 4.1 EventBus

The EventBus is the communication mechanism between event-producing and event-consuming components.

Responsibilities:

- Register event subscribers.
- Prevent duplicate registration of the same callback for an event type.
- Remove registered callbacks.
- Publish events to subscribers in subscription order.
- Continue dispatching when a subscriber raises an exception.
- Record subscriber failures in a bounded in-memory history.
- Log subscriber exceptions with traceback information.

The failure history retains up to 100 `SubscriberFailure` records. When the limit is reached, the oldest records are discarded as new failures arrive.

Each recorded failure contains the event, callback, and exception.

**Important behavior:** Event dispatch is synchronous. A callback runs as part of the publishing operation. Exceptions are caught by the EventBus so that a failing subscriber does not automatically prevent subsequent subscribers from running.

The failure history is in-memory diagnostic state, not persistent storage.

### 4.2 Market Session Management

The market session components coordinate market lifecycle events, including market opening and closing.

They allow downstream components to react to changes in the market session and initiate the appropriate processing or cleanup behavior.

### 4.3 MarketDataManager

The MarketDataManager manages incoming market-data events and publishes accepted ticks into the event-driven pipeline.

The existing tests verify tick publication and that ticks are ignored after market close.

The architecture separates incoming market data from downstream candle and strategy processing.

### 4.4 Candle Builder and Candle Scheduler

The candle components convert incoming ticks into time-based OHLC candle data.

Responsibilities include:

- Creating candles for symbols.
- Updating open, high, low, and close values.
- Keeping symbols' candle state independent.
- Creating new candles when an interval changes.
- Finalizing completed intervals.
- Publishing completed candle batches.

The scheduler coordinates interval boundaries and supports explicit finalization during market shutdown.

### 4.5 CandleSessionManager

The CandleSessionManager coordinates candle finalization when a market-close event occurs.

Its shutdown responsibilities include:

1. Receive the market-close event.
2. Check whether the boundary has already been successfully processed.
3. Ask the candle scheduler to finalize the boundary.
4. Record the boundary as processed after finalization succeeds.
5. Publish `MARKET_PROCESSING_COMPLETE`.

Recording the boundary only after successful finalization allows the same boundary to be retried if finalization raises an exception.

Repeated market-close events for an already successfully processed boundary do not publish duplicate completion events.

### 4.6 Indicator Engine

The indicator subsystem maintains indicator state and processes candle data.

The current test suite covers:

- Historical warmup behavior.
- EMA calculations.
- Incremental indicator updates.
- Independent state for multiple symbols.
- Indicator batch publication.
- Warmup-thread shutdown and cleanup.
- Cleanup triggered by `MARKET_PROCESSING_COMPLETE`.

### 4.7 Strategy Correlator

The correlator combines the relevant candle and indicator information into a strategy context.

It matches information using relevant attributes such as symbol and timeframe, preventing unrelated data from being combined.

Tests cover different event arrival orders, multiple symbols, and mismatched timeframes.

### 4.8 Strategy Dispatcher and Runtime

The strategy subsystem routes contexts and ticks to strategies that match the relevant symbol, timeframe, and strategy requirements.

The runtime is responsible for processing the data delivered to each strategy instance.

The existing tests cover EMA strategy behavior, strategy factory creation, routing, independent strategy instances, and signal generation.

### 4.9 Signal Distributor

The Signal Distributor delivers strategy signals to the appropriate subscribed users.

Its tests cover:

- Delivery to one or multiple subscribers.
- Exclusion of unsubscribed users.
- Matching the correct strategy group.
- Handling signals with no subscribers.
- Distribution monitoring events.

The distributor separates strategy signal generation from user-specific signal delivery.

### 4.10 Monitoring

The monitoring subsystem observes selected market-data, candle, indicator, strategy, and signal-distribution events.

Its purpose is to provide visibility into system activity without making the monitoring layer responsible for the core trading calculations.

---

## 5. Event and Error Handling

The EventBus uses callback-based event dispatch.

When a subscriber raises an exception:

1. The exception is caught by the EventBus.
2. A `SubscriberFailure` record is created.
3. The record is appended to the bounded failure history.
4. The exception is logged.
5. Dispatch continues to the remaining subscribers.

This approach improves fault isolation between subscribers.

However, catching a subscriber exception does not mean the failed operation succeeded. The EventBus records the failure for diagnostics but does not automatically retry the callback.

Retries must be implemented by the component responsible for the operation when retrying is appropriate.

---

## 6. Market Shutdown Lifecycle

Market shutdown is a critical lifecycle operation because incomplete candle processing can leave downstream components without the final data for an interval.

The current shutdown behavior is designed to:

1. Receive a market-close event.
2. Finalize the last candle boundary.
3. Publish the final candle data through the existing event pipeline.
4. Publish `MARKET_PROCESSING_COMPLETE` after successful finalization.
5. Allow downstream components to clean up their runtime state.
6. Avoid repeating successful finalization for the same boundary.

The tests also verify that a subscriber failure during candle-batch processing does not prevent the shutdown completion event from being published.

### Completion semantics

`MARKET_PROCESSING_COMPLETE` represents completion of the shutdown lifecycle after the candle-finalization operation returns successfully.

It does **not** guarantee that every subscriber processed every event successfully. Subscriber failures are recorded separately by the EventBus.

This distinction should be preserved when implementing future error reporting or operational monitoring.

---

## 7. Testing and Verification

The completed milestone has been verified using the project's automated test suite.

**Latest result:**

```text
224 passed, 2 warnings in 2.34s
```

The test suite includes coverage for:

- EventBus subscription and dispatch.
- Subscriber exception handling.
- Bounded subscriber failure history.
- Candle construction and scheduling.
- Market-data processing.
- Indicator calculation and lifecycle management.
- Strategy correlation and dispatch.
- Strategy signal generation and distribution.
- Market shutdown and runtime cleanup.
- Integration across multiple pipeline stages.

The two warnings are TLS-option deprecation warnings originating from the installed SmartApi dependency. They did not cause test failures.

Automated tests establish the behavior covered by those tests. They do not prove live-market correctness, broker reliability, or production readiness.

---

## 8. Known Boundaries of This Milestone

This milestone is focused on backend architecture and reliability.

The following capabilities should be treated as separate validation areas rather than assumed complete:

- Production-grade broker connectivity.
- Live order placement and fill reconciliation.
- Persistent recovery of in-memory runtime state.
- Durable storage of subscriber failures.
- Operational alerting and recovery procedures.
- Production deployment, security, and load testing.
- Live-trading validation and performance evaluation.

Some of these capabilities may exist elsewhere in the repository. Their status should be established by reviewing the corresponding implementation and tests before planning additional work.

---

## 9. Git and Version Control

The completed changes were committed and pushed to GitHub.

- **Repository:** `prabhu141206/trading-engine-service`
- **Branch:** `integration-testing`
- **Commit:** `198a0c6`
- **Commit message:** `Improve event failure tracking and shutdown retry safety`

The local Git remote was updated to the repository's current URL.

The working tree was clean after the commit.

---

## 10. Milestone Conclusion

The current backend architecture and reliability milestone is complete.

The implementation now has a tested event-driven processing pipeline, strategy routing and signal distribution, defined market-shutdown behavior, and improved visibility into subscriber failures.

The codebase should retain this passing test suite as a regression baseline for subsequent development.

Future work should begin with a separately defined requirement and build on this baseline rather than unnecessarily refactoring components that are already working.

**Milestone status: Completed.**
