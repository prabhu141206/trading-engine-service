from dataclasses import dataclass
from datetime import datetime

from event_system.event_type import EventType
from market_session.market_state import MarketState


@dataclass(frozen=True)
class NextMarketEvent:
    event: EventType
    event_time: datetime
    sleep_seconds: int
    market_state: MarketState