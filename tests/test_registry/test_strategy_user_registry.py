from strategy.strategy_models import StrategyGroup

from registry.strategy_user_registry import StrategyUserRegistry


def create_ema_nifty_group() -> StrategyGroup:
    """
    Create an EMA 10 strategy group for NIFTY.
    """
    return StrategyGroup(
        strategy_type="EMA",
        symbol="NIFTY",
        timeframe="5m",
        parameters=(("period", 10),),
    )


def create_ema_reliance_group() -> StrategyGroup:
    """
    Create an EMA 10 strategy group for RELIANCE.
    """
    return StrategyGroup(
        strategy_type="EMA",
        symbol="RELIANCE",
        timeframe="5m",
        parameters=(("period", 10),),
    )


def test_new_registry_has_no_subscribers():
    """
    A new registry should contain no user subscriptions.
    """
    registry = StrategyUserRegistry()

    group = create_ema_nifty_group()

    assert registry.get_subscribers(group) == set()


def test_user_can_subscribe_to_strategy_group():
    """
    Verify that one user can subscribe to a strategy group.
    """
    registry = StrategyUserRegistry()

    group = create_ema_nifty_group()

    registry.subscribe(
        user_id=101,
        group=group,
    )

    assert registry.get_subscribers(group) == {101}


def test_multiple_users_can_subscribe_to_same_group():
    """
    Multiple users can subscribe to the same strategy computation.
    """
    registry = StrategyUserRegistry()

    group = create_ema_nifty_group()

    registry.subscribe(101, group)
    registry.subscribe(102, group)
    registry.subscribe(103, group)

    assert registry.get_subscribers(group) == {
        101,
        102,
        103,
    }


def test_duplicate_subscription_does_not_duplicate_user():
    """
    Subscribing the same user multiple times must not create
    duplicate user IDs.
    """
    registry = StrategyUserRegistry()

    group = create_ema_nifty_group()

    registry.subscribe(101, group)
    registry.subscribe(101, group)

    assert registry.get_subscribers(group) == {101}


def test_different_strategy_groups_are_independent():
    """
    Users subscribed to one strategy group must not appear under
    another strategy group.
    """
    registry = StrategyUserRegistry()

    nifty_group = create_ema_nifty_group()
    reliance_group = create_ema_reliance_group()

    registry.subscribe(101, nifty_group)
    registry.subscribe(102, nifty_group)

    registry.subscribe(103, reliance_group)

    assert registry.get_subscribers(nifty_group) == {
        101,
        102,
    }

    assert registry.get_subscribers(reliance_group) == {
        103,
    }


def test_user_can_unsubscribe_from_strategy_group():
    """
    Verify that a user can be removed from a strategy group.
    """
    registry = StrategyUserRegistry()

    group = create_ema_nifty_group()

    registry.subscribe(101, group)
    registry.subscribe(102, group)

    registry.unsubscribe(
        user_id=101,
        group=group,
    )

    assert registry.get_subscribers(group) == {102}


def test_unsubscribe_nonexistent_user_does_nothing():
    """
    Removing a user who is not subscribed must not raise an error
    or affect existing subscribers.
    """
    registry = StrategyUserRegistry()

    group = create_ema_nifty_group()

    registry.subscribe(101, group)

    registry.unsubscribe(
        user_id=999,
        group=group,
    )

    assert registry.get_subscribers(group) == {101}


def test_unsubscribing_last_user_removes_group_subscription():
    """
    When the last user is removed, the strategy group should have
    no subscribers.
    """
    registry = StrategyUserRegistry()

    group = create_ema_nifty_group()

    registry.subscribe(101, group)

    registry.unsubscribe(
        user_id=101,
        group=group,
    )

    assert registry.get_subscribers(group) == set()


def test_clear_removes_all_subscriptions():
    """
    Verify that clear removes every strategy-user subscription.
    """
    registry = StrategyUserRegistry()

    nifty_group = create_ema_nifty_group()
    reliance_group = create_ema_reliance_group()

    registry.subscribe(101, nifty_group)
    registry.subscribe(102, nifty_group)
    registry.subscribe(103, reliance_group)

    registry.clear()

    assert registry.get_subscribers(nifty_group) == set()
    assert registry.get_subscribers(reliance_group) == set()


def test_get_subscribers_returns_copy():
    """
    Verify that callers cannot modify the registry's internal
    subscriber set through the returned value.
    """
    registry = StrategyUserRegistry()

    group = create_ema_nifty_group()

    registry.subscribe(101, group)

    subscribers = registry.get_subscribers(group)

    subscribers.add(999)

    assert registry.get_subscribers(group) == {101}