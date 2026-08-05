from datetime import time
from zoneinfo import ZoneInfo

# ==========================================================
# Setting up the time zone
# ==========================================================
IST = ZoneInfo("Asia/Kolkata")

class MarketConfig:
    """
    Market trading session configuration.
    """

    MARKET_OPEN = time(hour=9, minute=15)
    MARKET_CLOSE = time(hour=15, minute=30)