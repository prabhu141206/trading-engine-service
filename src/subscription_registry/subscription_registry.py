from collections import defaultdict

from session.user_session import UserSession


class SubscriptionRegistry:
    """
    In-memory index for user symbol subscriptions.

    Responsibilities
    ----------------
    - Map symbol -> users.
    - Map user -> symbols.
    - Maintain symbol reference counts.
    - Provide fast lookup for future market-data routing.
    """

    def __init__(self) -> None:

        # symbol -> {user_ids}
        self._symbol_to_users: dict[str, set[int]] = defaultdict(set)

        # user_id -> {symbols}
        self._user_to_symbols: dict[int, set[str]] = defaultdict(set)

        # symbol -> active subscription count
        self._symbol_counts: dict[str, int] = defaultdict(int)

    # ---------------------------------------------------------
    # Public API
    # ---------------------------------------------------------

    def add_session(
        self,
        session: UserSession
    ) -> None:
        """
        Register all symbol subscriptions for a user session.
        """

        for symbol in session.subscribed_symbols:

            self._symbol_to_users[symbol].add(session.user_id)
            self._user_to_symbols[session.user_id].add(symbol)
            self._symbol_counts[symbol] += 1

    def remove_session(
        self,
        user_id: int
    ) -> None:
        """
        Remove all subscriptions associated with a user session.
        """

        symbols = self._user_to_symbols.get(user_id, set()).copy()

        for symbol in symbols:

            self._symbol_to_users[symbol].discard(user_id)

            if not self._symbol_to_users[symbol]:
                del self._symbol_to_users[symbol]

            self._symbol_counts[symbol] -= 1

            if self._symbol_counts[symbol] <= 0:
                del self._symbol_counts[symbol]

        self._user_to_symbols.pop(user_id, None)

    def get_users(
        self,
        symbol: str
    ) -> set[int]:

        return self._symbol_to_users.get(symbol, set())

    def get_symbols(
        self,
        user_id: int
    ) -> set[str]:

        return self._user_to_symbols.get(user_id, set())

    def get_all_symbols(self) -> set[str]:

        return set(self._symbol_to_users.keys())

    def get_symbol_count(
        self,
        symbol: str
    ) -> int:

        return self._symbol_counts.get(symbol, 0)

    def clear(self) -> None:

        self._symbol_to_users.clear()
        self._user_to_symbols.clear()
        self._symbol_counts.clear()