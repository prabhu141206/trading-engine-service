# Database

The `db` module is responsible for persistent storage and database access
for the trading engine.

PostgreSQL acts as the persistent source of truth for users, strategy
definitions, strategy requirements, and user strategy subscriptions.

The runtime trading system does not use the database as a real-time data
transport. Database configuration is loaded into runtime objects when the
trading session starts.

---
## Purpose

The database layer provides:

- Persistent storage for users.
- Persistent storage for strategy templates.
- Persistent storage for strategy requirements.
- Persistent storage for user strategy subscriptions.
- SQLAlchemy ORM models for database tables.
- Database connection management and connection pooling.
- Repository-based access to user strategy configuration.
- Conversion of persistent configuration into runtime `UserSession` objects.

The database layer is intentionally separated from the runtime trading
components.

---

## Architecture

The database layer follows this flow:

```text
                    PostgreSQL
                        │
                        │
                        ▼
              UserSessionRepository
                        │
                        │
                        ▼
                   UserSession
                        │
                        ▼
                 SessionManager
                        │
             ┌──────────┼──────────┐
             ▼          ▼          ▼
       Subscription  Strategy   StrategyUser
         Registry    Registry     Registry
````

### Separation of responsibilities

The database is responsible for **persistent configuration**.

Runtime registries are responsible for **in-memory runtime state**.

For example:

```text
PostgreSQL
    │
    │ persistent configuration
    ▼
UserSessionRepository
    │
    │ converts DB data
    ▼
UserSession
    │
    ▼
SessionManager
    │
    ├── SubscriptionRegistry
    ├── StrategyRegistry
    └── StrategyUserRegistry
```

Components such as the market-data pipeline and strategy engine operate
using runtime state and do not query PostgreSQL directly.

---

# Database Schema

The database currently contains four tables:

```text
users
   │
   └──────────────┐
                  │
                  ▼
        strategy_subscriptions
                  │
                  ▼
          strategy_templates
                  │
                  ▼
        strategy_requirements
```

---

## `users`

Stores user account information.

| Column          | Description                |
| --------------- | -------------------------- |
| `id`            | Unique user identifier     |
| `email`         | User email address         |
| `password_hash` | Hashed password            |
| `is_active`     | Whether the user is active |
| `created_at`    | Record creation timestamp  |
| `updated_at`    | Last update timestamp      |

`is_active` determines whether the user participates in the active trading
configuration loaded at market startup.

---

## `strategy_templates`

Stores predefined strategy definitions.

| Column          | Description                             |
| --------------- | --------------------------------------- |
| `id`            | Unique strategy template identifier     |
| `name`          | Human-readable strategy name            |
| `strategy_type` | Runtime strategy type                   |
| `description`   | Strategy description                    |
| `is_active`     | Whether the strategy template is active |
| `created_at`    | Record creation timestamp               |
| `updated_at`    | Last update timestamp                   |

A strategy template represents a predefined strategy rather than executable
Python logic stored in the database.

For example:

```text
10 EMA Breakout Strategy
```

The actual strategy implementation remains in Python.

---

## `strategy_requirements`

Stores the requirements/configuration associated with a strategy template.

| Column                 | Description                               |
| ---------------------- | ----------------------------------------- |
| `id`                   | Unique requirement identifier             |
| `strategy_template_id` | Related strategy template                 |
| `requirement_type`     | Type of requirement                       |
| `name`                 | Requirement name                          |
| `parameters`           | Requirement configuration stored as JSONB |

Examples of requirements:

```text
INDICATOR
    EMA
    {"period": 10}
```

and:

```text
TIMEFRAME
    CANDLE
    {"value": "5m"}
```

The JSONB `parameters` field allows the requirement configuration to evolve
without requiring a new database column for every parameter.

---

## `strategy_subscriptions`

Stores which strategies users have subscribed to and for which symbols.

| Column                 | Description                        |
| ---------------------- | ---------------------------------- |
| `id`                   | Unique subscription identifier     |
| `user_id`              | Related user                       |
| `strategy_template_id` | Related strategy template          |
| `symbol`               | Trading symbol                     |
| `is_active`            | Whether the subscription is active |
| `created_at`           | Record creation timestamp          |
| `updated_at`           | Last update timestamp              |

The combination of:

```text
user_id
strategy_template_id
symbol
```

is unique.

Example:

```text
User 101 → 10 EMA Breakout → NIFTY
User 101 → 10 EMA Breakout → BANKNIFTY
User 202 → 10 EMA Breakout → NIFTY
User 303 → 10 EMA Breakout → FINNIFTY
```

---

# Runtime Flow

The database is not queried continuously during strategy execution.

At the beginning of a trading cycle:

```text
Market Open
    │
    ▼
SessionManager
    │
    ▼
UserSessionRepository
    │
    ▼
PostgreSQL
    │
    ▼
Active users + active subscriptions
    │
    ▼
UserSession objects
    │
    ▼
SessionManager
    │
    ├── SubscriptionRegistry
    ├── StrategyRegistry
    └── StrategyUserRegistry
```

The active configuration is determined using:

```text
users.is_active = true
strategy_subscriptions.is_active = true
strategy_templates.is_active = true
```

After the configuration has been loaded, the runtime components use the
in-memory registries.

At market close, the runtime session and registries are cleared.

---

# SQLAlchemy Models

SQLAlchemy is used as the ORM for database access.

The models are located under:

```text
db/models/
```

Current models:

```text
Base
 │
 ├── User
 ├── StrategyTemplate
 ├── StrategyRequirement
 └── StrategySubscription
```

The declarative base is defined in:

```text
db/models/base.py
```

Each ORM model maps to its corresponding PostgreSQL table.

The repository uses SQLAlchemy queries instead of embedding raw SQL strings
inside the application logic.

---

# Connection Pooling

Database connections are managed through SQLAlchemy's connection pool.

The engine is configured using environment-based settings.

Current configuration includes:

```text
DB_POOL_SIZE
DB_MAX_OVERFLOW
DB_POOL_TIMEOUT
DB_POOL_RECYCLE
```

Connection pooling allows database connections to be reused instead of
creating a new database connection for every operation.

The database engine also uses connection pre-ping to detect stale
connections before they are used.

Database credentials are not hardcoded in the source code.

---

# Repository

## `UserSessionRepository`

The repository provides the database access required to construct active
runtime user sessions.

```text
db/user_session_repository.py
```

Its main operation is:

```python
get_active_sessions()
```

The repository:

1. Reads active users.
2. Reads their active strategy subscriptions.
3. Reads the corresponding active strategy templates.
4. Loads the strategy requirements.
5. Converts database configuration into `StrategyGroup` objects.
6. Groups subscriptions and strategies by user.
7. Returns `UserSession` objects.

Conceptually:

```text
Database rows
     │
     ▼
UserSessionRepository
     │
     ├── User
     ├── StrategySubscription
     ├── StrategyTemplate
     └── StrategyRequirement
     │
     ▼
StrategyGroup
     │
     ▼
UserSession
```

The repository therefore acts as the boundary between persistent database
configuration and the runtime session model.

---

# Environment Configuration

Database configuration is provided through environment variables.

Example:

```env
DATABASE_URL=postgresql+psycopg2://postgres:<password>@localhost:5432/algomind

DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=1800
```

The application loads these values through the settings module.

Sensitive values such as database passwords should remain in `.env` and
should not be committed to version control.

A `.env.example` file can be used to document the required environment
variables without exposing secrets.

---

# Testing

The database layer has tests covering:

### Database connection

Verifies that the application can establish a connection to PostgreSQL.

### ORM models

Tests reading data through:

```text
User
StrategyTemplate
StrategyRequirement
StrategySubscription
```

### UserSessionRepository

Tests that persistent database configuration is correctly converted into
runtime `UserSession` objects.

The repository test verifies that users, symbols, strategies, timeframes,
and strategy parameters are reconstructed correctly.

The complete project test suite currently passes:

```text
180 passed
```

---

# Important Design Decisions

## 1. PostgreSQL is the persistent source of truth

User and strategy configuration must survive application restarts.

Runtime registries are therefore not persistent storage.

---

## 2. Runtime registries remain in memory

The following registries are runtime structures:

```text
SubscriptionRegistry
StrategyRegistry
StrategyUserRegistry
```

They are rebuilt from persistent database configuration when a trading
session starts.

---

## 3. Database is not used for real-time signal transport

The database is not part of the hot path for:

```text
Tick
  ↓
Candle
  ↓
Indicator
  ↓
Strategy
  ↓
Signal
```

Real-time processing uses the application's runtime event system and
in-memory structures.

---

## 4. Runtime components do not query PostgreSQL directly

Components such as:

```text
MarketDataManager
IndicatorEngine
StrategyEngine
SignalDistributor
```

should not independently query the database for configuration.

Database access is isolated behind the repository layer.

---

## 5. Strategy logic remains in Python

The database stores strategy configuration and requirements.

It does not store executable strategy logic.

For example, the database can describe:

```text
EMA
period = 10
timeframe = 5m
```

while the actual breakout strategy implementation remains in Python.

---

## 6. Active configuration is cycle-based

The system loads active configuration when the trading cycle starts.

A strategy subscription added or changed during an active cycle is persisted
in the database but does not automatically modify the already-running
runtime configuration.

The updated configuration participates in the next trading cycle.

There is no separate `is_scheduled` field because scheduling is handled by
the market-cycle lifecycle.

---

## 7. Repository performs database-to-runtime mapping

The database representation does not have to be identical to the runtime
representation.

`UserSessionRepository` is responsible for translating persistent
configuration into the runtime objects expected by the trading engine.

This keeps database concerns separate from strategy and session logic.


I think this is a good **first version**: technical enough for a developer joining the project, but not unnecessarily huge.


