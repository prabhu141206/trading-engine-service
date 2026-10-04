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

'''
Coverage: SessionManager startup/event subscription.
It proves that SessionManager.start() subscribes 
its market-open handler to the EventBus.

'''
def test_subscribe_market_open():
    manager, event_bus, _, _, _ = create_manager()

    manager.start()

    assert len(
        event_bus._subscribers[EventType.MARKET_OPEN]
    ) == 1



'''
    Coverage:

    MARKET_OPEN
        ↓
    SessionManager
        ↓
    StrategyRegistry

    It verifies both quantity and 
    contents of the strategy groups.
'''

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

    '''
    Coverage:

    MARKET_OPEN
        ↓
    SessionManager
        ↓
    StrategyUserRegistry

    This is particularly useful because it 
    checks that the relationship between user and strategy 
    is preserved.
    '''
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


def test_market_processing_complete_clears_runtime_state():
    """
    Verify that market processing completion clears
    user sessions and all runtime registries.
    """

    (
        manager,
        event_bus,
        subscription_registry,
        strategy_registry,
        strategy_user_registry,
    ) = create_manager()

    manager.start()

    # MARKET_OPEN creates the actual runtime session state.
    event_bus.publish(
        Event(
            event_type=EventType.MARKET_OPEN,
            payload=None,
        )
    )

    # Verify runtime state exists before cleanup.
    assert manager._sessions
    assert subscription_registry.get_symbols()

    assert strategy_registry.get_groups()

    assert (
        strategy_user_registry.get_subscribers(
            StrategyGroup(
                strategy_type="EMA",
                symbol="NIFTY",
                timeframe="5m",
                parameters=(("period", 10),),
            )
        )
        == {101, 202}
    )

    # Trigger market-processing completion.
    event_bus.publish(
        Event(
            event_type=EventType.MARKET_PROCESSING_COMPLETE,
            payload=None,
        )
    )

    # All runtime state must now be cleared.
    assert manager._sessions == {}

    assert subscription_registry.get_symbols() == set()

    assert strategy_registry.get_groups() == set()

    assert (
        strategy_user_registry.get_subscribers(
            StrategyGroup(
                strategy_type="EMA",
                symbol="NIFTY",
                timeframe="5m",
                parameters=(("period", 10),),
            )
        )
        == set()
    )