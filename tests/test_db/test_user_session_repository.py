from db.user_session_repository import UserSessionRepository


def test_get_active_sessions():
    # Create the repository responsible for loading
    # persistent user configuration from PostgreSQL.
    repository = UserSessionRepository()

    # Load the active configuration and convert it
    # into the runtime UserSession objects.
    sessions = repository.get_active_sessions()

    # Our demo database contains active users,
    # so the repository should return sessions.
    assert len(sessions) > 0

    # Print the result so we can compare it with
    # our previous hardcoded _load_active_users().
    for session in sessions:
        print(f"\nUser ID: {session.user_id}")

        print(
            f"Subscribed symbols: "
            f"{session.subscribed_symbols}"
        )

        print("Strategies:")

        for strategy in session.strategies:
            print(
                f"  {strategy.strategy_type} | "
                f"{strategy.symbol} | "
                f"{strategy.timeframe} | "
                f"{strategy.parameters}"
            )