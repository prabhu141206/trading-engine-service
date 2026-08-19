from event_system.event_bus import EventBus

from registry.subscription_registry import SubscriptionRegistry
from registry.strategy_registry import StrategyRegistry

from session.session_manager import SessionManager

from market_data.market_data_manager import MarketDataManager
from market_data.fake_websocket_client import FakeWebSocketClient

from candle.candle_builder import CandleBuilder
from candle.candle_scheduler import CandleScheduler
from candle.candle_timeframe import CandleTimeframe


def main():

    # =========================================================
    # Core Infrastructure
    # =========================================================

    event_bus = EventBus()

    subscription_registry = SubscriptionRegistry()

    strategy_registry = StrategyRegistry()

    # =========================================================
    # External Connections
    # =========================================================

    websocket_client = FakeWebSocketClient()

    # =========================================================
    # Session Management
    # =========================================================

    session_manager = SessionManager(
        event_bus=event_bus,
        subscription_registry=subscription_registry,
        strategy_registry=strategy_registry,
    )

    # =========================================================
    # Market Data
    # =========================================================

    market_data_manager = MarketDataManager(
        event_bus=event_bus,
        subscription_registry=subscription_registry,
        websocket_client=websocket_client,
    )

    # =========================================================
    # Candle System
    # =========================================================

    candle_builder = CandleBuilder(
        event_bus=event_bus,
    )

    candle_scheduler = CandleScheduler(
        timeframe=CandleTimeframe.FIVE_MINUTES,
        on_boundary=candle_builder.finalize_interval,
    )

    # =========================================================
    # Start Components
    # =========================================================

    session_manager.start()

    market_data_manager.start()

    candle_builder.start()

    candle_scheduler.start()


if __name__ == "__main__":
    main()