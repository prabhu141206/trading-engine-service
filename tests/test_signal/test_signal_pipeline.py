from datetime import datetime
from unittest.mock import Mock

from event_system.event import Event
from event_system.event_bus import EventBus
from event_system.event_type import EventType

from registry.strategy_user_registry import StrategyUserRegistry
from signal_distribution.signal_delivery import SignalDelivery
from signal_distribution.signal_distributor import SignalDistributor
from strategy.strategy_models import StrategyGroup
from strategy.strategy_output import (
    SignalSide,
    SignalType,
    StrategyOutput,
)


def create_group(
    symbol: str,
) -> StrategyGroup:
    return StrategyGroup(
        strategy_type="EMA",
        symbol=symbol,
        timeframe="5m",
        parameters=(("period", 10),),
    )


def create_signal(
    group: StrategyGroup,
) -> StrategyOutput:
    return StrategyOutput(
        strategy_group=group,
        signal_type=SignalType.ENTRY,
        side=SignalSide.BUY,
        timestamp=datetime(2026, 8, 28, 10, 20),
    )


def test_strategy_signal_reaches_only_matching_users():
    """
    Verify the complete signal-distribution path.

    Flow:

        STRATEGY_SIGNAL_GENERATED
                    ↓
             EventBus
                    ↓
          SignalDistributor
                    ↓
        StrategyUserRegistry
                    ↓
             subscribed users
                    ↓
             SignalDelivery

    Users:
        101 → EMA + NIFTY
        102 → EMA + NIFTY
        103 → EMA + RELIANCE

    Generated signal:
        EMA + NIFTY → BUY ENTRY

    Expected:
        101 receives the signal
        102 receives the signal
        103 does not receive the signal
    """

    # ---------------------------------------------------------
    # Create real components
    # ---------------------------------------------------------

    event_bus = EventBus()
    registry = StrategyUserRegistry()

    # Delivery is the external boundary.
    # We don't implement WebSocket yet.
    delivery = Mock(spec=SignalDelivery)

    distributor = SignalDistributor(
        event_bus=event_bus,
        subscription_registry=registry,
        delivery=delivery,
    )

    # ---------------------------------------------------------
    # Start distributor
    # ---------------------------------------------------------

    distributor.start()

    # ---------------------------------------------------------
    # Create subscriptions
    # ---------------------------------------------------------

    nifty_group = create_group("NIFTY")
    reliance_group = create_group("RELIANCE")

    registry.subscribe(
        user_id=101,
        group=nifty_group,
    )

    registry.subscribe(
        user_id=102,
        group=nifty_group,
    )

    registry.subscribe(
        user_id=103,
        group=reliance_group,
    )

    # ---------------------------------------------------------
    # Generate NIFTY signal
    # ---------------------------------------------------------

    signal = create_signal(nifty_group)

    signal_event = Event(
        event_type=EventType.STRATEGY_SIGNAL_GENERATED,
        payload=signal,
    )

    # ---------------------------------------------------------
    # Publish through the real EventBus
    # ---------------------------------------------------------

    event_bus.publish(signal_event)

    # ---------------------------------------------------------
    # Verify delivery
    # ---------------------------------------------------------

    assert delivery.deliver.call_count == 2

    delivery.deliver.assert_any_call(
        user_id=101,
        signal=signal,
    )

    delivery.deliver.assert_any_call(
        user_id=102,
        signal=signal,
    )

    # User 103 belongs to RELIANCE, not NIFTY.
    assert not any(
        call.kwargs["user_id"] == 103
        for call in delivery.deliver.call_args_list
    )