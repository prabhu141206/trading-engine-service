from dataclasses import dataclass
from datetime import datetime

from market_session.market_event import MarketEvent


@dataclass(frozen=True)
class NextMarketEvent:
    """
    Represents the next scheduled market event.
    """

    event: MarketEvent
    event_time: datetime
    sleep_seconds: int