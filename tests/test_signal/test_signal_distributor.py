from datetime import datetime
from unittest.mock import Mock

from signal_distribution.signal_distributor import SignalDistributor
from strategy.strategy_models import StrategyGroup
from strategy.strategy_output import (
    SignalSide,
    SignalType,
    StrategyOutput,
)
from registry.strategy_user_registry import StrategyUserRegistry


def create_ema_nifty_group() -> StrategyGroup:
    """
    Create the EMA 10 + NIFTY strategy group used by the tests.
    """
    return StrategyGroup(
        strategy_type="EMA",
        symbol="NIFTY",
        timeframe="5m",
        parameters=(("period", 10),),
    )


def create_ema_reliance_group() -> StrategyGroup:
    """
    Create a different strategy group to verify isolation.
    """
    return StrategyGroup(
        strategy_type="EMA",
        symbol="RELIANCE",
        timeframe="5m",
        parameters=(("period", 10),),
    )


def create_signal(
    group: StrategyGroup,
) -> StrategyOutput:
    """
    Create a deterministic strategy signal.
    """
    return StrategyOutput(
        strategy_group=group,
        signal_type=SignalType.ENTRY,
        side=SignalSide.BUY,
        timestamp=datetime(2026, 8, 28, 10, 20),
    )


def create_distributor():
    """
    Create a SignalDistributor with a mocked EventBus,
    real StrategyUserRegistry, and mocked delivery mechanism.
    """
    event_bus = Mock()
    registry = StrategyUserRegistry()
    delivery = Mock()

    distributor = SignalDistributor(
        event_bus=event_bus,
        subscription_registry=registry,
        delivery=delivery,
    )

    return distributor, registry, delivery

def test_signal_is_delivered_to_one_subscribed_user():
    """
    A signal should be delivered to a user subscribed to its
    exact StrategyGroup.
    """
    distributor, registry, delivery = create_distributor()

    group = create_ema_nifty_group()
    signal = create_signal(group)

    registry.subscribe(
        user_id=101,
        group=group,
    )

    distributor.distribute(signal)

    delivery.deliver.assert_called_once_with(
        user_id=101,
        signal=signal,
    )


def test_signal_is_delivered_to_all_subscribed_users():
    """
    Every user subscribed to the same StrategyGroup should receive
    the generated signal.
    """
    distributor, registry, delivery = create_distributor()

    group = create_ema_nifty_group()
    signal = create_signal(group)

    registry.subscribe(101, group)
    registry.subscribe(102, group)
    registry.subscribe(103, group)

    distributor.distribute(signal)

    assert delivery.deliver.call_count == 3

    delivery.deliver.assert_any_call(
        user_id=101,
        signal=signal,
    )

    delivery.deliver.assert_any_call(
        user_id=102,
        signal=signal,
    )

    delivery.deliver.assert_any_call(
        user_id=103,
        signal=signal,
    )


def test_signal_is_not_delivered_to_unsubscribed_user():
    """
    A user who is not subscribed to the signal's StrategyGroup
    must not receive the signal.
    """
    distributor, registry, delivery = create_distributor()

    group = create_ema_nifty_group()
    signal = create_signal(group)

    registry.subscribe(101, group)

    distributor.distribute(signal)

    delivery.deliver.assert_called_once_with(
        user_id=101,
        signal=signal,
    )

    assert not any(
        call.kwargs.get("user_id") == 102
        for call in delivery.deliver.call_args_list
    )


def test_signal_only_reaches_users_of_matching_strategy_group():
    """
    Users subscribed to a different StrategyGroup must not receive
    the signal.
    """
    distributor, registry, delivery = create_distributor()

    nifty_group = create_ema_nifty_group()
    reliance_group = create_ema_reliance_group()

    signal = create_signal(nifty_group)

    registry.subscribe(101, nifty_group)
    registry.subscribe(102, reliance_group)

    distributor.distribute(signal)

    delivery.deliver.assert_called_once_with(
        user_id=101,
        signal=signal,
    )


def test_signal_with_no_subscribers_is_not_delivered():
    """
    If nobody is subscribed to the StrategyGroup, no delivery should
    occur.
    """
    distributor, _, delivery = create_distributor()

    group = create_ema_nifty_group()
    signal = create_signal(group)

    distributor.distribute(signal)

    delivery.deliver.assert_not_called()


def test_same_signal_object_is_delivered_to_each_user():
    """
    The distributor should distribute the generated StrategyOutput
    itself rather than creating different strategy outputs per user.
    """
    distributor, registry, delivery = create_distributor()

    group = create_ema_nifty_group()
    signal = create_signal(group)

    registry.subscribe(101, group)
    registry.subscribe(102, group)

    distributor.distribute(signal)

    delivered_signals = [
        call.kwargs["signal"]
        for call in delivery.deliver.call_args_list
    ]

    assert delivered_signals == [
        signal,
        signal,
    ]