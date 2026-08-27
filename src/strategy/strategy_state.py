from enum import Enum


class StrategyState(str, Enum):
    """
    Runtime state of a strategy instance.
    """

    IDLE = "IDLE"
    TRIGGER_ARMED = "TRIGGER_ARMED"
    IN_TRADE = "IN_TRADE"


class TradeDirection(str, Enum):
    """
    Direction of the active strategy setup/trade.
    """

    LONG = "LONG"
    SHORT = "SHORT"