from registry.subscription_registry import SubscriptionRegistry


def test_add_symbol():
    """
    Test Case:
    Verify that a single symbol can be added to the subscription registry.

    Expected Result:
    The added symbol should be present in the registry.
    """
    registry = SubscriptionRegistry()

    registry.add_symbol("NIFTY")

    assert registry.get_symbols() == {"NIFTY"}


def test_add_multiple_symbols():
    """
    Test Case:
    Verify that multiple different symbols can be added to the
    subscription registry.

    Expected Result:
    All added symbols should be present in the registry.
    """
    registry = SubscriptionRegistry()

    registry.add_symbol("NIFTY")
    registry.add_symbol("BANKNIFTY")
    registry.add_symbol("RELIANCE")

    assert registry.get_symbols() == {
        "NIFTY",
        "BANKNIFTY",
        "RELIANCE",
    }


def test_duplicate_symbol_is_registered_only_once():
    """
    Test Case:
    Verify that adding the same symbol multiple times does not
    create duplicate entries.

    Expected Result:
    The symbol should appear only once in the registry.
    """
    registry = SubscriptionRegistry()

    registry.add_symbol("NIFTY")
    registry.add_symbol("NIFTY")

    assert registry.get_symbols() == {"NIFTY"}


def test_remove_symbol():
    """
    Test Case:
    Verify that an existing symbol can be removed from the
    subscription registry.

    Expected Result:
    The specified symbol should be removed while other symbols
    remain registered.
    """
    registry = SubscriptionRegistry()

    registry.add_symbol("NIFTY")
    registry.add_symbol("BANKNIFTY")

    registry.remove_symbol("NIFTY")

    assert registry.get_symbols() == {"BANKNIFTY"}


def test_remove_non_existing_symbol():
    """
    Test Case:
    Verify that removing a symbol that is not registered does
    not affect existing subscriptions.

    Expected Result:
    The existing symbol should remain in the registry and
    no error should occur.
    """
    registry = SubscriptionRegistry()

    registry.add_symbol("NIFTY")

    registry.remove_symbol("BANKNIFTY")

    assert registry.get_symbols() == {"NIFTY"}


def test_get_symbols_returns_copy():
    """
    Test Case:
    Verify that get_symbols() returns a copy of the internal
    symbol set instead of exposing the registry's internal state.

    Expected Result:
    Modifying the returned set should not modify the actual
    subscription registry.
    """
    registry = SubscriptionRegistry()

    registry.add_symbol("NIFTY")

    symbols = registry.get_symbols()

    # Modify the returned set.
    # This must not affect the internal registry.
    symbols.add("BANKNIFTY")

    assert registry.get_symbols() == {"NIFTY"}