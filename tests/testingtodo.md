Absolutely. Here is the **Phase 2 TODO checklist** we should follow. We can tick these off one by one and **not move ahead until the current flow is proven**.

# 🧪 Phase 2 — Integration & Runtime Testing TODO

## A. Candle Pipeline

* [✅] **1. Test Tick → CandleBuilder**

  * Tick reaches CandleBuilder ✅
  * Correct 5-minute bucket  ✅
  * First tick creates candle ✅
  * Subsequent ticks update OHLC ✅

* [ ] **2. Test candle interval transition**

  * New 5-minute interval starts
  * Previous candle is finalized correctly

* [ ] **3. Test CandleBatch creation**

  * Correct symbol(s)
  * Correct timeframe
  * Correct start/end time
  * Correct OHLC

* [ ] **4. Test `CANDLE_BATCH_CLOSED` event**

  * CandleBuilder publishes event
  * IndicatorEngine receives it
  * StrategyEngine receives it

---

## B. Indicator Pipeline

* [ ] **5. Test live CandleBatch → IndicatorEngine**

* [ ] **6. Test EMA-10 calculation/update**

  * Correct symbol
  * Correct timeframe
  * Correct EMA value

* [ ] **7. Test IndicatorBatch creation**

* [ ] **8. Test indicator event flow**

  * `INDICATOR_BATCH_UPDATED`
  * Correct payload
  * Correct consumers receive it

---

## C. Candle + Indicator Correlation

* [ ] **9. Test StrategyCorrelator receives CandleBatch**

* [ ] **10. Test StrategyCorrelator receives IndicatorBatch**

* [ ] **11. Test matching**

  * Same symbol
  * Same timeframe
  * Same start time
  * Same end time

* [ ] **12. Test `StrategyContext` creation**

Expected:

```text
CandleBatch
     +
IndicatorBatch
     ↓
StrategyCorrelator
     ↓
StrategyContext
```

---

## D. EMA Strategy — Context Path

* [ ] **13. Test StrategyEngine receives StrategyContext**

* [ ] **14. Test Dispatcher routes context to correct EMA strategy**

* [ ] **15. Test `EMA.on_context()`**

* [ ] **16. Test EMA trigger conditions**

  * Bearish candle + no EMA touch → LONG arm
  * Bullish candle + no EMA touch → SHORT arm
  * EMA-touch candle → no trigger

* [ ] **17. Test state transition**

```text
IDLE
 ↓
TRIGGER_ARMED
```

---

## E. EMA Strategy — Tick Path

* [ ] **18. Test tick after trigger is armed**

* [ ] **19. Test Dispatcher routes tick to armed strategy**

* [ ] **20. Test `EMA.on_tick()`**

* [ ] **21. Test LONG breakout**

  * Tick > trigger candle high
  * State → `IN_TRADE`
  * BUY output

* [ ] **22. Test SHORT breakout**

  * Tick < trigger candle low
  * State → `IN_TRADE`
  * SELL output

---

## F. Strategy Output

* [ ] **23. Test `StrategyOutput` creation**

Verify:

```text
strategy_group
signal_type
side
timestamp
```

* [ ] **24. Test StrategyEngine publishes output**

* [ ] **25. Test `STRATEGY_SIGNAL_GENERATED` event**

* [ ] **26. Test SignalDistributor receives output**

---

# 🔥 G. Full End-to-End Test

* [ ] **27. Run complete flow with one strategy**

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
StrategyCorrelator
 ↓
StrategyContext
 ↓
EMA.on_context()
 ↓
TRIGGER_ARMED
 ↓
Breakout Tick
 ↓
EMA.on_tick()
 ↓
StrategyOutput
 ↓
SignalDistributor
```

---

# 👥 H. Multi-User Test

* [ ] **28. Multiple users using same symbol**

Example:

```text
User 101 → NIFTY EMA
User 202 → NIFTY EMA
```

* [ ] **29. Verify shared market data**

* [ ] **30. Verify strategies don't interfere with each other's state**

* [ ] **31. Different symbols simultaneously**

```text
NIFTY
BANKNIFTY
FINNIFTY
```

* [ ] **32. Verify correct strategy routing**

---

# 🔄 I. Lifecycle Testing

* [ ] **33. MARKET_OPEN**

* [ ] **34. Sessions reconstructed**

* [ ] **35. Strategies created**

* [ ] **36. Subscriptions created**

* [ ] **37. MARKET_CLOSE**

* [ ] **38. Sessions cleaned**

* [ ] **39. Registries cleaned**

* [ ] **40. Strategies cleaned/reset**

* [ ] **41. Next MARKET_OPEN reconstructs everything**

---

# 🔁 J. Restart / Recovery

* [ ] **42. Stop application**

* [ ] **43. Start application again**

* [ ] **44. Verify DB remains source of truth**

* [ ] **45. Verify runtime registries are rebuilt**

* [ ] **46. Verify strategies are recreated**

* [ ] **47. Verify subscriptions are recreated**

---

# 🛡️ K. Failure Testing

* [ ] **48. WebSocket disconnect**

* [ ] **49. WebSocket reconnect**

* [ ] **50. Unknown strategy type**

* [ ] **51. Missing candle**

* [ ] **52. Missing indicator**

* [ ] **53. Unknown symbol**

* [ ] **54. Strategy exception**

* [ ] **55. Verify one user's failure doesn't break other users**

---

# 🏁 Phase 2 Completion Criteria

We should consider Phase 2 complete only when this works:

```text id="f9e6e1"
              PostgreSQL
                   ↓
             SessionManager
                   ↓
          ┌────────┴────────┐
          ↓                 ↓
 SubscriptionRegistry   StrategyRegistry
          ↓                 ↓
    MarketDataManager  StrategyFactory
          ↓                 ↓
         Tick          Strategies
          │                 │
          └───────┬─────────┘
                  ↓
            CandleBuilder
                  ↓
             CandleBatch
                  ↓
           IndicatorEngine
                  ↓
            IndicatorBatch
                  ↓
          StrategyCorrelator
                  ↓
           StrategyContext
                  ↓
            EMA Strategy
                  ↓
            Trigger Armed
                  ↓
             Breakout Tick
                  ↓
            StrategyOutput
                  ↓
          Signal Distribution
```

**Our immediate TODO is only #1: Tick → CandleBuilder → proper candle formation.**

We'll work through this list **one checkbox at a time**, with the same process we've been following:

**Problem → Why → Caller → Input → Output → Code → Run → Verify.**
