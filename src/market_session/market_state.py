from enum import Enum


class MarketState(Enum):
    """
    Represents the current market session state.
    """

    OPEN = "OPEN"
    CLOSED = "CLOSED"