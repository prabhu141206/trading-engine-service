from subscription_registry.subscription_registry import SubscriptionRegistry
from session.user_session import UserSession


def test_add_single_user_session():

    registry = SubscriptionRegistry()

    session = UserSession(
        user_id=101,
        subscribed_symbols={"NIFTY", "BANKNIFTY"}
    )

    registry.add_session(session)

    assert registry.get_users("NIFTY") == {101}
    assert registry.get_users("BANKNIFTY") == {101}
    assert registry.get_symbols(101) == {"NIFTY", "BANKNIFTY"}


def test_symbol_reference_count():

    registry = SubscriptionRegistry()

    registry.add_session(
        UserSession(
            user_id=101,
            subscribed_symbols={"NIFTY"}
        )
    )

    registry.add_session(
        UserSession(
            user_id=202,
            subscribed_symbols={"NIFTY"}
        )
    )

    assert registry.get_symbol_count("NIFTY") == 2

    registry.remove_session(101)

    assert registry.get_symbol_count("NIFTY") == 1

    registry.remove_session(202)

    assert registry.get_symbol_count("NIFTY") == 0