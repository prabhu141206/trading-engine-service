from strategy.strategy_models import StrategyGroup


class StrategyUserRegistry:
    """
    Maps strategy computation groups to the users subscribed to them.

    Responsibilities:
        - Register a user for a strategy group.
        - Remove a user from a strategy group.
        - Return users subscribed to a strategy group.
        - Clear all strategy-user subscriptions.

    This class does not:
        - create strategy objects
        - generate signals
        - publish events
        - execute orders
        - send notifications
    """

    def __init__(self) -> None:
        self._subscriptions: dict[
            StrategyGroup,
            set[int],
        ] = {}

    def subscribe(
        self,
        user_id: int,
        group: StrategyGroup,
    ) -> None:
        """Subscribe a user to a strategy group."""

        self._subscriptions.setdefault(
            group,
            set(),
        ).add(user_id)

    def unsubscribe(
        self,
        user_id: int,
        group: StrategyGroup,
    ) -> None:
        """Remove a user from a strategy group."""

        users = self._subscriptions.get(group)

        if users is None:
            return

        users.discard(user_id)

        if not users:
            self._subscriptions.pop(group, None)

    def get_subscribers(
        self,
        group: StrategyGroup,
    ) -> set[int]:
        """Return users subscribed to a strategy group."""

        return self._subscriptions.get(
            group,
            set(),
        ).copy()

    def clear(self) -> None:
        """Remove all strategy-user subscriptions."""

        self._subscriptions.clear()