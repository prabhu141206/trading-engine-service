from dataclasses import dataclass, field
from registry.strategy_models import StrategyGroup

@dataclass
class UserSession:
    user_id: int
    subscribed_symbols: set[str]
    strategies: set[StrategyGroup] = field(default_factory=set)