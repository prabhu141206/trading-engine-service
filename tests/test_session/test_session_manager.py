from event_system.event import Event
from event_system.event_bus import EventBus
from event_system.event_type import EventType

from registry.subscription_registry import SubscriptionRegistry
from registry.strategy_registry import StrategyRegistry
from registry.strategy_user_registry import StrategyUserRegistry
from session.session_manager import SessionManager
from strategy.strategy_models import StrategyGroup
from db.user_session_repository import UserSessionRepository


def create_manager():
    """
    Create a SessionManager with all required dependencies.
    """
    event_bus = EventBus()
    subscription_registry = SubscriptionRegistry()
    strategy_registry = StrategyRegistry()
    strategy_user_registry = StrategyUserRegistry()
    user_session_repository = UserSessionRepository()

    manager = SessionManager(
        event_bus=event_bus,
        subscription_registry=subscription_registry,
        strategy_registry=strategy_registry,
        strategy_user_registry=strategy_user_registry,
        user_session_repository=user_session_repository,
    )

    return (
        manager,
        event_bus,
        subscription_registry,
        strategy_registry,
        strategy_user_registry,
    )


def test_subscribe_market_open():
    manager, event_bus, _, _, _ = create_manager()

    manager.start()

    assert len(
        event_bus._subscribers[EventType.MARKET_OPEN]
    ) == 1


def test_subscribe_market_close():
    manager, event_bus, _, _, _ = create_manager()

    manager.start()

    assert len(
        event_bus._subscribers[EventType.MARKET_CLOSE]
    ) == 1


def test_market_open_populates_subscription_registry():
    (
        manager,
        event_bus,
        subscription_registry,
        _,
        _,
    ) = create_manager()

    manager.start()

    event_bus.publish(
        Event(
            event_type=EventType.MARKET_OPEN,
            payload=None,
        )
    )

    assert subscription_registry.get_symbols() == {
        "NIFTY",
        "BANKNIFTY",
        "FINNIFTY",
    }


def test_market_open_populates_strategy_registry():
    (
        manager,
        event_bus,
        _,
        strategy_registry,
        _,
    ) = create_manager()

    manager.start()

    event_bus.publish(
        Event(
            event_type=EventType.MARKET_OPEN,
            payload=None,
        )
    )

    strategies = strategy_registry.get_groups()

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


def test_market_open_populates_strategy_user_registry():
    (
        manager,
        event_bus,
        _,
        _,
        strategy_user_registry,
    ) = create_manager()

    manager.start()

    event_bus.publish(
        Event(
            event_type=EventType.MARKET_OPEN,
            payload=None,
        )
    )

    ema_nifty = StrategyGroup(
        strategy_type="EMA",
        symbol="NIFTY",
        timeframe="5m",
        parameters=(("period", 10),),
    )

    ema_banknifty = StrategyGroup(
        strategy_type="EMA",
        symbol="BANKNIFTY",
        timeframe="5m",
        parameters=(("period", 10),),
    )

    ema_finnifty = StrategyGroup(
        strategy_type="EMA",
        symbol="FINNIFTY",
        timeframe="5m",
        parameters=(("period", 10),),
    )

    assert (
        strategy_user_registry.get_subscribers(ema_nifty)
        == {101, 202}
    )

    assert (
        strategy_user_registry.get_subscribers(ema_banknifty)
        == {101}
    )

    assert (
        strategy_user_registry.get_subscribers(ema_finnifty)
        == {303}
    )