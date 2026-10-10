# Shutdown Testing and Findings

## 1. Objective

Verify that the trading engine shuts down safely at market close, finalizes the last candle, publishes the completion event in the correct order, and cleans up runtime resources without duplicate processing.

## 2. Shutdown Flow

1. `MARKET_CLOSE` is published.
2. `MarketDataManager` stops accepting new ticks.
3. `CandleSessionManager` requests finalization of the last candle boundary.
4. `CandleBuilder` publishes `CANDLE_BATCH_CLOSED` when an active candle exists for that interval.
5. `CandleSessionManager` publishes `MARKET_PROCESSING_COMPLETE`.
6. Downstream components clear runtime state or disconnect resources.

The event bus processes subscribers synchronously in registration order.

## 3. Issue 1 — Final Candle Could Be Skipped

### Cause

`CandleScheduler.stop_after_boundary()` originally returned immediately if the scheduler was not running. This prevented the final boundary callback from running when the scheduler had never been started.

### Impact

`MARKET_PROCESSING_COMPLETE` could be published without the final candle being finalized.

### Fix

Changed `stop_after_boundary()` to trigger the final boundary before checking whether the scheduler is running.

### Verification

Added a regression test that publishes a tick, leaves the scheduler stopped, and then publishes `MARKET_CLOSE`. The test verifies that the candle batch is published before the completion event.

### Status

Fixed and committed.

Commit: `10a3c22` — `fix: finalize last candle during market shutdown`

## 4. Issue 2 — Duplicate Completion Events

### Cause

`CandleSessionManager._on_market_close()` publishes `MARKET_PROCESSING_COMPLETE` every time it receives `MARKET_CLOSE`.

### Reproduction

Publish the same market-close event twice after building a candle.

Observed behavior:
- Candle batches published: 1
- Completion events published: 2

### Expected Behavior

Repeated market-close events should not initiate shutdown more than once. Only one completion event should be published for the same shutdown lifecycle.

### Proposed Fix

Add an `_shutdown_started` guard to `CandleSessionManager`. Set the flag before finalization and return immediately when a duplicate market-close event is received.

### Verification Required

- The repeated-close regression test must pass.
- All shutdown tests must pass.
- The full test suite must pass.
- Inspect the diff before committing.

### Status

Bug reproduced. Fix proposed but not yet verified.

## 5. Test Coverage

| Test | Purpose |
|---|---|
| `test_full_market_shutdown_finalizes_candle_before_completion` | Verifies final candle publication precedes completion. |
| `test_market_close_does_not_silently_skip_final_candle_when_scheduler_is_stopped` | Verifies finalization when the scheduler was never started. |
| `test_repeated_market_close_publishes_completion_only_once` | Verifies that repeated market close produces one completion event. |

## 6. Event Bus Findings

- Subscribers execute synchronously in registration order.
- Subscriber exceptions are caught and printed.
- The bus continues processing later subscribers after a handler raises an exception.

These behaviors must be considered when evaluating shutdown ordering and failure recovery.

## 7. Remaining Work

1. Verify and implement shutdown idempotency.
2. Rerun shutdown tests and the full test suite.
3. Inspect the final diff and commit the verified change.
4. Continue auditing downstream final-candle processing and resource cleanup.
