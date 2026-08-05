from enum import Enum


class MarketState(Enum):
    """
    Represents the current state of the market session.
    """

    WAITING = "WAITING"
    OPEN = "OPEN"
    CLOSED = "CLOSED"