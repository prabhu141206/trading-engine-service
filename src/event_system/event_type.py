from enum import Enum


class EventType(Enum):

    # MARKET SESSION EVENTS
    MARKET_OPEN = "MARKET_OPEN"
    MARKET_CLOSE = "MARKET_CLOSE"