


# Strategy

The `strategy` module is responsible for executing trading strategy logic
using runtime market data, candle information, and indicator state.

The strategy layer is separated from:

- Market data ingestion
- Tick caching
- Candle construction
- Indicator calculation
- User session management
- Signal distribution
- Database access

The strategy layer consumes prepared runtime market information and produces
strategy outputs/signals.

---

## 1. Purpose

The `strategy` module is responsible for:

- Defining strategy configuration.
- Defining strategy requirements.
- Creating concrete strategy instances.
- Correlating candle and indicator information.
- Creating strategy contexts.
- Routing contexts and ticks to the correct strategies.
- Executing strategy logic.
- Producing strategy outputs.
- Publishing strategy signals through the event system.

The strategy implementation itself remains in Python.

The database stores strategy configuration and requirements, but it does not
store executable strategy logic.


---

# 2. Strategy Architecture

The main strategy execution flow is:

```text
                  Candle Events
                       │
                       │
                  Indicator Events
                       │
                       ▼
               StrategyCorrelator
                       │
                       ▼
                StrategyContext
                       │
                       ▼
              StrategyDispatcher
                       │
                       ▼
               Concrete Strategy
                       │
                       ▼
                StrategyOutput
                       │
                       ▼
          STRATEGY_SIGNAL_GENERATED
````

The `StrategyEngine` coordinates this flow:

```text
Candle Event
     │
     ▼
StrategyEngine
     │
     ▼
StrategyCorrelator
     │
     ▼
StrategyContext
     │
     ▼
StrategyDispatcher
     │
     ▼
Concrete Strategy
     │
     ▼
StrategyOutput
     │
     ▼
STRATEGY_SIGNAL_GENERATED
```

For tick-based strategies, ticks can be dispatched directly:

```text
Tick Event
    │
    ▼
StrategyEngine
    │
    ▼
StrategyDispatcher
    │
    ▼
Tick-aware Strategy
    │
    ▼
StrategyOutput
    │
    ▼
STRATEGY_SIGNAL_GENERATED
```

---

# 3. Strategy Components

The strategy module contains several components, each with a specific
responsibility.

```text
strategy/
│
├── strategy_models.py
├── strategy_requirements.py
├── strategy_context.py
├── strategy_output.py
├── strategy_factory.py
├── strategy_dispatcher.py
├── strategy_correlator.py
├── strategy_engine.py
└── concrete strategy implementations
```

The major components are:

```text
Strategy Models
Strategy Requirements
Strategy Context
Strategy Correlator
Strategy Factory
Strategy Dispatcher
Strategy Engine
Concrete Strategies
Strategy Output
```

---

# 4. Strategy Models

`StrategyGroup` represents the runtime configuration of a strategy.

A strategy group contains:

```text
strategy_type
symbol
timeframe
parameters
```

For example:

```python
StrategyGroup(
    strategy_type="EMA",
    symbol="NIFTY",
    timeframe="5m",
    parameters=(("period", 10),),
)
```

A `StrategyGroup` identifies a particular strategy computation group.

For example:

```text
EMA + NIFTY + 5m + period 10
```

is a different strategy group from:

```text
EMA + BANKNIFTY + 5m + period 10
```

This allows different symbols and configurations to be processed
independently.

---

# 5. Strategy Requirements

Strategy requirements describe the information required by a strategy.

Examples include:

```text
TIMEFRAME
INDICATOR
TICK
```

For example, the current EMA-based strategy requires:

```text
Timeframe:
    5m

Indicator:
    EMA(10)
```

Requirements are used by the strategy infrastructure to determine what
market information is required before a strategy can make a decision.

The requirements describe what the strategy needs, while the strategy
implementation contains the actual trading logic.

---

# 6. Strategy Context

`StrategyContext` represents the correlated runtime information provided to
a strategy.

The context allows the strategy to evaluate the required market state
without directly accessing the candle builder, indicator engine, or other
components.

Conceptually:

```text
Candle
   +
Indicator State
   │
   ▼
StrategyContext
   │
   ▼
Strategy
```

This keeps strategy logic focused on decision making instead of data
collection and coordination.

---

# 7. Strategy Correlator

`StrategyCorrelator` is responsible for combining related market
information before it is sent to a strategy.

For a strategy requiring both candle and indicator information:

```text
Candle Event
     │
     │
     ├──────────────┐
     │              │
     ▼              ▼
  Candle       Indicator Event
     │              │
     └───────┬──────┘
             │
             ▼
      StrategyContext
```

A candle event alone does not create a complete strategy context.

An indicator event alone does not create a complete strategy context.

When the required pieces for the same symbol and interval are available,
the correlator creates a `StrategyContext`.

## Correlation Rules

Correlation is performed independently using:

* Symbol
* Time interval

Therefore:

```text
NIFTY + 5m
```

is not correlated with:

```text
BANKNIFTY + 5m
```

and:

```text
NIFTY + 5m
```

is not correlated with:

```text
NIFTY + 15m
```

This prevents unrelated market information from being combined.

---

# 8. Strategy Factory

`StrategyFactory` is responsible for creating concrete strategy instances
from a `StrategyGroup`.

Conceptually:

```text
StrategyGroup
     │
     ▼
StrategyFactory
     │
     ├── EMA → EMAStrategy
     └── Other supported strategies
```

The factory hides concrete strategy construction from the rest of the
system.

The caller provides the strategy configuration, and the factory creates
the appropriate strategy implementation.

Example:

```python
strategy = strategy_factory.create(strategy_group)
```

The factory also rejects unsupported strategy types.

---

# 9. Strategy Dispatcher

`StrategyDispatcher` routes runtime market information to the correct
strategy instances.

Routing is based on the strategy configuration and incoming market data.

For example:

```text
Incoming Context
    │
    ├── Symbol = NIFTY
    ├── Timeframe = 5m
    │
    ▼
Matching Strategy
```

A strategy configured for:

```text
NIFTY + 5m
```

should not receive a context for:

```text
BANKNIFTY + 5m
```

Similarly:

```text
NIFTY + 5m
```

should not receive:

```text
NIFTY + 15m
```

Tick-based strategies are also routed according to their requirements.

A strategy that does not require ticks does not receive tick events.

This keeps each strategy isolated from unrelated market data.

---

# 10. Strategy Engine

`StrategyEngine` coordinates the strategy execution pipeline.

It subscribes to the relevant events and connects the strategy components
together.

## Candle and Indicator Flow

```text
Candle Event
     │
     ▼
StrategyCorrelator
     │
     ▼
Completed StrategyContext
     │
     ▼
StrategyDispatcher
     │
     ▼
Strategy
```

Indicator events follow the same correlation process:

```text
Indicator Event
     │
     ▼
StrategyCorrelator
     │
     ▼
Completed StrategyContext
     │
     ▼
StrategyDispatcher
     │
     ▼
Strategy
```

## Tick Flow

For strategies requiring tick information:

```text
Tick Event
     │
     ▼
StrategyEngine
     │
     ▼
StrategyDispatcher
     │
     ▼
Tick-aware Strategy
```

The `StrategyEngine` does not query PostgreSQL.

It works with runtime strategy objects and runtime events.

---

# 11. Concrete Strategy

The current product strategy is the:

## 10 EMA Breakout Strategy

The current strategy configuration is:

```text
Strategy:
    10 EMA Breakout Strategy

Indicator:
    EMA

EMA Period:
    10

Timeframe:
    5m
```

The strategy maintains its own runtime state.

Conceptually, its state flow is:

```text
Idle
  │
  ▼
Trigger Armed
  │
  ▼
Breakout
  │
  ▼
Trade Active
  │
  ▼
Exit
  │
  ▼
Idle
```

The strategy reacts to the appropriate candle, indicator, and tick
information according to its requirements.

The actual breakout and trade-management rules are implemented inside the
Python strategy implementation.

---

# 12. Strategy Output

A strategy does not directly deliver a signal to users.

Instead, it produces a `StrategyOutput`.

The output can represent actions such as:

```text
Entry
Exit
```

An entry can represent:

```text
BUY
SELL
```

An exit represents the strategy's decision to leave the current trade.

Conceptually:

```text
Concrete Strategy
       │
       ▼
StrategyOutput
       │
       ├── Entry
       │     ├── BUY
       │     └── SELL
       │
       └── Exit
```

The strategy output is then passed into the signal flow.

---

# 13. Strategy Signal Flow

Once a strategy generates an output:

```text
Strategy
   │
   ▼
StrategyOutput
   │
   ▼
StrategyEngine
   │
   ▼
STRATEGY_SIGNAL_GENERATED
```

The event is then consumed by the signal distribution layer.

```text
STRATEGY_SIGNAL_GENERATED
            │
            ▼
     SignalDistributor
            │
            ▼
    StrategyUserRegistry
            │
            ▼
       SignalDelivery
```

The strategy module does not know which users should receive a signal.

User-specific signal delivery is handled by the signal distribution layer.

This keeps strategy decision-making separate from signal delivery.

---

# 14. Multiple Strategy Groups

Multiple users can subscribe to the same strategy group.

For example:

```text
EMA + NIFTY + 5m + period 10
              │
              ├── User 101
              └── User 202
```

Only one runtime strategy computation group is required for this
configuration.

The relationship between the strategy group and users is maintained
separately by the `StrategyUserRegistry`.

This prevents unnecessary duplicate strategy calculations.

---

# 15. Independent Strategy Groups

Different configurations create independent strategy groups.

For example:

```text
EMA + NIFTY + 5m + period 10
EMA + BANKNIFTY + 5m + period 10
```

are separate strategy groups.

Similarly:

```text
EMA + NIFTY + 5m + period 10
EMA + NIFTY + 15m + period 10
```

are separate groups because their timeframes are different.

Each strategy group has its own computation and runtime state.

---

# 16. Database Boundary

The strategy module does not directly access PostgreSQL.

Persistent strategy configuration is loaded by the database/repository layer
and converted into runtime strategy configuration.

The flow is:

```text
PostgreSQL
    │
    ▼
UserSessionRepository
    │
    ▼
StrategyGroup
    │
    ▼
StrategyRegistry
    │
    ▼
StrategyFactory
    │
    ▼
Concrete Strategy
```

The database therefore provides persistent configuration, while the
strategy module provides executable behavior.

The database is not part of the real-time strategy execution path.

---

# 17. Runtime Lifecycle

Strategy runtime objects are created as part of the trading session
configuration.

At market open:

```text
Market Open
    │
    ▼
SessionManager
    │
    ▼
Load Active Configuration
    │
    ▼
StrategyRegistry
    │
    ▼
Runtime Strategy Groups
```

During the trading session:

```text
Market Data
    │
    ▼
Events
    │
    ▼
StrategyEngine
    │
    ▼
Strategy Components
    │
    ▼
Concrete Strategy
    │
    ▼
Strategy Output
    │
    ▼
Strategy Signal
```

At market close, the runtime strategy state is cleared along with the
runtime session configuration.

Persistent strategy configuration remains in PostgreSQL.

---

# 18. Testing

The strategy layer is tested at multiple levels.

## Strategy Models

Tests cover:

* Identical strategy groups are equal.
* Different parameters create different groups.
* Different symbols create different groups.

## Strategy Requirements

Tests cover:

* Default requirements.
* EMA requirements.
* Requirement immutability.

## Strategy Factory

Tests cover:

* Creating supported strategies.
* Passing configuration correctly.
* Creating independent strategy instances.
* Rejecting unsupported strategies.

## Strategy Dispatcher

Tests cover:

* Matching symbols.
* Matching timeframes.
* Different strategy configurations.
* Tick routing.
* Preventing tick delivery to strategies that do not require ticks.

## Strategy Correlator

Tests cover:

* Candle alone does not create a context.
* Indicator alone does not create a context.
* Matching candle and indicator data creates a context.
* Different symbols remain independent.
* Different intervals remain independent.

## Strategy Engine

Tests cover:

* Event subscriptions.
* Candle event handling.
* Indicator event handling.
* Completed context dispatch.
* Multiple completed contexts.
* Direct tick dispatch.

## Concrete Strategy

The current EMA strategy tests cover:

* Initial idle state.
* Long trigger arming.
* Short trigger arming.
* Candle touching EMA behavior.
* Long breakout entry.
* Short breakout entry.
* Maintaining an armed trigger.
* Long trade exit.
* Short trade exit.
* Ignoring new triggers while already in a trade.

## Integration

Integration tests verify that:

```text
StrategyRegistry
       ↓
StrategyFactory
       ↓
StrategyDispatcher
       ↓
Concrete Strategy
```

works together correctly and that strategy outputs are converted into
strategy signal events.

---

# 19. Important Design Decisions

## 19.1 Strategy logic remains in Python

The database stores strategy configuration and requirements.

Executable trading logic is implemented in Python.

This keeps strategy behavior version-controlled, testable, and separate
from persistent configuration.

---

## 19.2 StrategyEngine does not access the database

`StrategyEngine` operates using runtime strategy objects and events.

It does not query PostgreSQL during strategy execution.

This keeps database operations outside the real-time strategy path.

---

## 19.3 Strategy computation is independent of user count

If multiple users subscribe to the same strategy group:

```text
EMA + NIFTY + 5m
       │
       ├── User 101
       ├── User 202
       └── User 303
```

the strategy computation is performed once.

The `StrategyUserRegistry` maintains the user-to-strategy relationship
separately.

---

## 19.4 Strategy routing is configuration-based

Strategies receive only market information matching their configuration and
requirements.

Routing considers information such as:

* Symbol
* Timeframe
* Required data type

This prevents unrelated market data from reaching a strategy.

---

## 19.5 Strategy does not handle signal delivery

A strategy is responsible for making a trading decision.

It does not know:

* Which users subscribed.
* How signals are delivered.
* Whether delivery uses WebSocket.
* How risk management is performed.
* How order execution is performed.

These responsibilities belong to downstream components.

---

## 19.6 Runtime strategy state is kept in memory

Strategy objects maintain their runtime state in memory.

Persistent strategy configuration is stored in PostgreSQL.

After an application restart, runtime strategy configuration is rebuilt
from persistent configuration.

---

## 19.7 Different strategy groups are independently computed

A difference in strategy configuration creates a separate strategy group.

Examples:

```text
EMA + NIFTY + 5m
EMA + BANKNIFTY + 5m
EMA + NIFTY + 15m
```

are independently represented and processed.

This prevents state and calculations from different strategy configurations
from being mixed.

---

## 19.8 Strategy is separated from signal distribution

The strategy layer determines **what signal was generated**.

The signal distribution layer determines **who should receive that signal**.

This separation keeps the strategy implementation independent of users and
delivery mechanisms.

---

# Overall Strategy Flow

The complete strategy architecture can be summarized as:

```text
                         PostgreSQL
                              │
                              ▼
                   UserSessionRepository
                              │
                              ▼
                       StrategyGroup
                              │
                              ▼
                     StrategyRegistry
                              │
                              ▼
                      StrategyFactory
                              │
                              ▼
                    Concrete Strategy
                              ▲
                              │
                     StrategyDispatcher
                              ▲
                              │
                       StrategyEngine
                              ▲
                              │
                     StrategyCorrelator
                         ▲          ▲
                         │          │
                      Candle     Indicator
                       Events      Events


Concrete Strategy
       │
       ▼
StrategyOutput
       │
       ▼
STRATEGY_SIGNAL_GENERATED
       │
       ▼
SignalDistributor
       │
       ▼
StrategyUserRegistry
       │
       ▼
SignalDelivery
```

The strategy layer is therefore the **decision-making layer** of the
trading engine.

It consumes prepared runtime market information, evaluates the strategy
logic, and produces strategy outputs without directly depending on
database access or user-specific signal delivery.

