from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Tick:
    """
    Immutable market tick.
    """

    symbol: str
    price: float
    timestamp: datetime