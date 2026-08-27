from strategy.strategy_models import StrategyGroup

class StrategyRegistry:
    """
    Stores unique strategy computation groups.

    Responsibilities:
        - Register strategy groups.
        - Remove strategy groups.
        - Return all registered groups.

    This class does not create strategy objects.
    """

    def __init__(self) -> None:
        self._groups: set[StrategyGroup] = set()

    def add_group(self, group: StrategyGroup) -> None:
        """Register a strategy group."""
        self._groups.add(group)

    def remove_group(self, group: StrategyGroup) -> None:
        """Remove a strategy group."""
        self._groups.discard(group)

    def get_groups(self) -> set[StrategyGroup]:
        """Return a copy of all registered strategy groups."""
        return self._groups.copy()

    def clear(self) -> None:
        """Remove all registered strategy groups."""
        self._groups.clear()