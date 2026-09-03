from datetime import datetime
from unittest.mock import Mock

from event_system.event import Event
from event_system.event_type import EventType
from registry.strategy_user_registry import StrategyUserRegistry
from signal_distribution.signal_distributor import SignalDistributor
from strategy.strategy_models import StrategyGroup
from strategy.strategy_output import (
    SignalSide,
    SignalType,
    StrategyOutput,
)


def create_group() -> StrategyGroup:
    return StrategyGroup(
        strategy_type="EMA",
        symbol="NIFTY",
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


def create_distributor():
    event_bus = Mock()
    registry = StrategyUserRegistry()
    delivery = Mock()

    distributor = SignalDistributor(
        event_bus=event_bus,
        subscription_registry=registry,
        delivery=delivery,
    )

    return distributor, event_bus, registry, delivery


def test_distributor_subscribes_to_strategy_signal_event():
    """
    SignalDistributor must subscribe to STRATEGY_SIGNAL_GENERATED
    when started.
    """
    distributor, event_bus, _, _ = create_distributor()

    distributor.start()

    event_bus.subscribe.assert_called_once_with(
        EventType.STRATEGY_SIGNAL_GENERATED,
        distributor._on_strategy_signal,
    )


def test_strategy_signal_event_is_distributed_to_subscribers():
    """
    A STRATEGY_SIGNAL_GENERATED event should be received by the
    distributor and delivered to every subscribed user.
    """
    distributor, _, registry, delivery = create_distributor()

    group = create_group()
    signal = create_signal(group)

    registry.subscribe(101, group)
    registry.subscribe(102, group)

    event = Event(
        event_type=EventType.STRATEGY_SIGNAL_GENERATED,
        payload=signal,
    )

    distributor._on_strategy_signal(event)

    assert delivery.deliver.call_count == 2

    delivery.deliver.assert_any_call(
        user_id=101,
        signal=signal,
    )

    delivery.deliver.assert_any_call(
        user_id=102,
        signal=signal,
    )


def test_strategy_signal_event_is_not_delivered_to_other_strategy_users():
    """
    Users subscribed to another StrategyGroup must not receive
    the signal.
    """
    distributor, _, registry, delivery = create_distributor()

    nifty_group = create_group()

    reliance_group = StrategyGroup(
        strategy_type="EMA",
        symbol="RELIANCE",
        timeframe="5m",
        parameters=(("period", 10),),
    )

    signal = create_signal(nifty_group)

    registry.subscribe(101, nifty_group)
    registry.subscribe(102, reliance_group)

    event = Event(
        event_type=EventType.STRATEGY_SIGNAL_GENERATED,
        payload=signal,
    )

    distributor._on_strategy_signal(event)

    delivery.deliver.assert_called_once_with(
        user_id=101,
        signal=signal,
    )


def test_strategy_signal_with_no_subscribers_causes_no_delivery():
    """
    A generated signal with no subscribed users should produce
    no delivery.
    """
    distributor, _, _, delivery = create_distributor()

    group = create_group()
    signal = create_signal(group)

    event = Event(
        event_type=EventType.STRATEGY_SIGNAL_GENERATED,
        payload=signal,
    )

    distributor._on_strategy_signal(event)

    delivery.deliver.assert_not_called()