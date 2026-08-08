# Trading Engine Service

Production-style event-driven algorithmic trading backend architecture built in Python.

## Main Branch

The `main` branch contains all completed modules and acts as the cumulative architecture reference.


## Architecture Goals

- Event-driven communication
- Loose coupling between services
- Multi-user session orchestration
- Shared market data distribution
- Scalable strategy runtime design
- Production-style modular architecture

---

## Current Modules

| Module | Status |
|--------|--------|
| Event System | Complete |
| Market Session Manager | Complete |
| Session Manager | Complete |
| Subscription Registry | Planned |
| Market Data Manager | Planned |
| Strategy Runtime | Planned |
| Trading Engine | Planned |

---

## Repository Structure

```text
trading-engine-service/
├── docs/
├── src/
│   ├── event_system/
│   ├── market_session/
│   └── session/
└── tests/
```

---

## Documentation

- [01 Event System](docs/01_event_system.md)
- [02 Market Session Manager](docs/02_market_session_manager.md)
- [03 Session Manager](docs/03_session_manager.md)

---

## Tech Stack

- Python 3.13
- Pytest
- Dataclasses
- Event-driven architecture
- Thread-based scheduling
- Modular backend design

---

## Testing

```bash
python -m pytest
```

---

## Development Workflow

Each subsystem is developed in an isolated feature branch and merged into `main` only after:

1. Design freeze
2. Implementation
3. Unit testing
4. Integration testing
5. Documentation

---

## Roadmap

- Subscription Registry
- Shared WebSocket Manager
- Symbol Router
- Indicator Engine
- Strategy Runtime Isolation
- Risk Management Layer
- Order Execution Layer
- Monitoring & Metrics

---

## License

MIT License
