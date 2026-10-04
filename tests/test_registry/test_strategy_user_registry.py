from strategy.strategy_models import StrategyGroup
from registry.strategy_user_registry import StrategyUserRegistry


def create_ema_nifty_group() -> StrategyGroup:
    """
    Create a standard EMA(10) strategy group for NIFTY.

    This helper is reused across multiple test cases to keep
    the strategy configuration consistent.
    """
    return StrategyGroup(
        strategy_type="EMA",
        symbol="NIFTY",
        timeframe="5m",
        parameters=(("period", 10),),
    )


def create_ema_reliance_group() -> StrategyGroup:
    """
    Create a standard EMA(10) strategy group for RELIANCE.

    This is used when testing whether different strategy groups
    maintain independent user subscriptions.
    """
    return StrategyGroup(
        strategy_type="EMA",
        symbol="RELIANCE",
        timeframe="5m",
        parameters=(("period", 10),),
    )


def test_new_registry_has_no_subscribers():
    """
    Test Case:
    Verify that a newly created StrategyUserRegistry contains
    no user subscriptions.

    Expected Result:
    get_subscribers() should return an empty set for a strategy
    group that has not been subscribed to by any user.
    """
    registry = StrategyUserRegistry()

    group = create_ema_nifty_group()

    assert registry.get_subscribers(group) == set()


def test_user_can_subscribe_to_strategy_group():
    """
    Test Case:
    Verify that a single user can subscribe to a strategy group.

    Expected Result:
    The user's ID should appear in the subscriber set of
    the specified strategy group.
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
    Test Case:
    Verify that multiple users can subscribe to the same
    strategy computation group.

    Expected Result:
    All subscribed user IDs should be present in the
    subscriber set of the strategy group.
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
    Test Case:
    Verify that subscribing the same user to the same strategy
    group multiple times does not create duplicate entries.

    Expected Result:
    The subscriber set should contain the user ID only once.
    """
    registry = StrategyUserRegistry()

    group = create_ema_nifty_group()

    registry.subscribe(101, group)
    registry.subscribe(101, group)

    assert registry.get_subscribers(group) == {101}


def test_different_strategy_groups_are_independent():
    """
    Test Case:
    Verify that subscriptions belonging to different strategy
    groups remain independent.

    Expected Result:
    Users subscribed to the NIFTY strategy group should not
    appear as subscribers of the RELIANCE strategy group,
    and vice versa.
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
    Test Case:
    Verify that a user can be removed from a strategy group.

    Expected Result:
    The specified user should be removed while other
    subscribers remain unaffected.
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
    Test Case:
    Verify that attempting to unsubscribe a user who is not
    subscribed does not cause an error or modify existing
    subscriptions.

    Expected Result:
    Existing subscribers should remain unchanged.
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
    Test Case:
    Verify that removing the last subscriber from a strategy
    group results in no remaining subscribers.

    Expected Result:
    get_subscribers() should return an empty set.
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
    Test Case:
    Verify that clear() removes all strategy-user subscriptions
    across all strategy groups.

    Expected Result:
    Every strategy group should have an empty subscriber set
    after clear() is called.
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
    Test Case:
    Verify that get_subscribers() returns a copy of the internal
    subscriber set rather than exposing the registry's internal
    data structure.

    Expected Result:
    Modifying the returned set should not modify the actual
    subscriptions stored inside the registry.
    """
    registry = StrategyUserRegistry()

    group = create_ema_nifty_group()

    registry.subscribe(101, group)

    subscribers = registry.get_subscribers(group)

    # Modify the returned set.
    # This must not affect the registry's internal state.
    subscribers.add(999)

    assert registry.get_subscribers(group) == {101}