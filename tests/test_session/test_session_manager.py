from event_system.event import Event
from event_system.event_bus import EventBus
from event_system.event_type import EventType
from session.session_manager import SessionManager
from registry.subscription_registry import SubscriptionRegistry
from registry.strategy_registry import StrategyRegistry


def test_subscribe_market_open():
    event_bus = EventBus()
    subscription_registry = SubscriptionRegistry()
    strategy_registry = StrategyRegistry()

    manager = SessionManager(
        event_bus=event_bus,
        subscription_registry=subscription_registry,
        strategy_registry=strategy_registry,
    )

    manager.start()

    assert len(
        event_bus._subscribers[EventType.MARKET_OPEN]
    ) == 1

def test_subscribe_market_close():
    event_bus = EventBus()
    subscription_registry = SubscriptionRegistry()
    strategy_registry = StrategyRegistry()

    manager = SessionManager(
        event_bus=event_bus,
        subscription_registry=subscription_registry,
        strategy_registry=strategy_registry,
    )

    manager.start()

    assert len(
        event_bus._subscribers[EventType.MARKET_CLOSE]
    ) == 1


def test_market_open_populates_subscription_registry():

    # Arrange
    event_bus = EventBus()
    subscription_registry = SubscriptionRegistry()
    strategy_registry = StrategyRegistry()

    manager = SessionManager(
        event_bus=event_bus,
        subscription_registry=subscription_registry,
        strategy_registry=strategy_registry,
    )

    manager.start()

    # Act
    event_bus.publish(
        Event(
            event_type=EventType.MARKET_OPEN,
            payload=None,
        )
    )

    # Assert
    assert subscription_registry.get_symbols() == {
        "NIFTY",
        "BANKNIFTY",
        "FINNIFTY",
    }


def test_market_open_populates_strategy_registry():

    # Arrange
    event_bus = EventBus()
    subscription_registry = SubscriptionRegistry()
    strategy_registry = StrategyRegistry()

    manager = SessionManager(
        event_bus=event_bus,
        subscription_registry=subscription_registry,
        strategy_registry=strategy_registry,
    )

    manager.start()

    # Act
    event_bus.publish(
        Event(
            event_type=EventType.MARKET_OPEN,
            payload=None,
        )
    )

    # Assert
    strategies = strategy_registry.get_strategies()

    assert len(strategies) == 3

    assert {
        (
            strategy.strategy_type,
            strategy.symbol,
            strategy.timeframe,
            strategy.parameters,
        )
        for strategy in strategies
    } == {
        ("EMA", "NIFTY", "5m", (("period", 10),)),
        ("EMA", "BANKNIFTY", "5m", (("period", 10),)),
        ("EMA", "FINNIFTY", "5m", (("period", 10),)),
    }