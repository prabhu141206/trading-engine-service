from registry.subscription_registry import SubscriptionRegistry


def test_add_symbol():
    registry = SubscriptionRegistry()

    registry.add_symbol("NIFTY")

    assert registry.get_symbols() == {"NIFTY"}


def test_add_multiple_symbols():
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
    registry = SubscriptionRegistry()

    registry.add_symbol("NIFTY")
    registry.add_symbol("NIFTY")

    assert registry.get_symbols() == {"NIFTY"}


def test_remove_symbol():
    registry = SubscriptionRegistry()

    registry.add_symbol("NIFTY")
    registry.add_symbol("BANKNIFTY")

    registry.remove_symbol("NIFTY")

    assert registry.get_symbols() == {"BANKNIFTY"}


def test_remove_non_existing_symbol():
    registry = SubscriptionRegistry()

    registry.add_symbol("NIFTY")

    registry.remove_symbol("BANKNIFTY")

    assert registry.get_symbols() == {"NIFTY"}


def test_get_symbols_returns_copy():
    registry = SubscriptionRegistry()

    registry.add_symbol("NIFTY")

    symbols = registry.get_symbols()
    symbols.add("BANKNIFTY")

    assert registry.get_symbols() == {"NIFTY"}