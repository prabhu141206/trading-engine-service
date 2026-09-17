"""
Application bootstrap.

This module is responsible for constructing and wiring
the application's runtime dependencies.
"""

# =========================================================
# Event System
# =========================================================

from event_system.event_bus import EventBus

# =========================================================
# Runtime Registries
# =========================================================

from registry.subscription_registry import SubscriptionRegistry
from registry.strategy_registry import StrategyRegistry
from registry.strategy_user_registry import StrategyUserRegistry


# =========================================================
# Session Management + Data Access
# =========================================================

from db.user_session_repository import UserSessionRepository
from session.session_manager import SessionManager

# ========================================================
# Market Session Management
# ========================================================

from market_session.market_calendar import MarketCalendar
from market_session.market_scheduler import MarketScheduler
from market_session.market_session_manager import MarketSessionManager


# =========================================================
# Market Data
# =========================================================

from market_data.market_data_manager import MarketDataManager
from broker.angel_one.authentication import AngelOneAuthenticator
from broker.angel_one.instrument_master import AngelOneInstrumentMaster
from broker.angel_one.websocket import AngelOneWebSocket

# =========================================================
# Tick Cache
# =========================================================

from tick_cache.tick_cache import TickCache


# =========================================================
# Candle System
# =========================================================

from candle.candle_builder import CandleBuilder
from candle.candle_scheduler import CandleScheduler
from candle.candle_timeframe import CandleTimeframe


# =========================================================
# Indicators
# =========================================================

from indicators.indicator_engine import IndicatorEngine
from indicators.indicator_state import IndicatorStateStore
from tvDatafeed import TvDatafeed
from market_data.tvdatafeed_historical import (
    TvDatafeedHistoricalProvider,
)

# =========================================================
# Strategy System
# =========================================================

from strategy.strategy_correlator import StrategyCorrelator
from strategy.strategy_dispatcher import StrategyDispatcher
from strategy.strategy_factory import StrategyFactory
from strategy.strategy_engine import StrategyEngine

# =========================================================
# Signal Distribution
# =========================================================

from signal_distribution.signal_distributor import SignalDistributor
from signal_distribution.signal_delivery import SignalDelivery
from signal_distribution.log_signal_delivery import LogSignalDelivery





def build_application():
    """
    Create and wire all application components.

    This function acts as the composition root of the
    application. It is responsible only for constructing
    components and injecting their dependencies.
    """

    # =====================================================
    # Core Infrastructure
    # =====================================================

    event_bus = EventBus()

    # =====================================================
    # Runtime Registries
    # =====================================================

    subscription_registry = SubscriptionRegistry()
    strategy_registry = StrategyRegistry()
    strategy_user_registry = StrategyUserRegistry()

    # =====================================================
    # Persistent Data Access
    # =====================================================

    user_session_repository = UserSessionRepository()

    # =====================================================
    # Market Session Management
    # =====================================================

    market_calendar = MarketCalendar()

    market_scheduler = MarketScheduler(
        calendar=market_calendar,
    )

    market_session_manager = MarketSessionManager(
        scheduler=market_scheduler,
        event_bus=event_bus,
        force_market_open=True,  # For testing purposes, force the market to open immediately
    )

    # =====================================================
    # Session Management
    # =====================================================

    session_manager = SessionManager(
        event_bus=event_bus,
        subscription_registry=subscription_registry,
        strategy_registry=strategy_registry,
        strategy_user_registry=strategy_user_registry,
        user_session_repository=user_session_repository,
    )

    # =====================================================
    # Market Data
    # =====================================================

    authenticator = AngelOneAuthenticator()

    instrument_master = AngelOneInstrumentMaster()
    instrument_master.load()

    websocket_client = AngelOneWebSocket(
        authenticator=authenticator,
        instrument_master=instrument_master,
    )

    market_data_manager = MarketDataManager(
        event_bus=event_bus,
        subscription_registry=subscription_registry,
        websocket_client=websocket_client,
    )

    # =====================================================
    # Tick Cache
    # =====================================================

    tick_cache = TickCache(
        event_bus=event_bus,
    )

    # =====================================================
    # Candle System
    # =====================================================

    candle_builder = CandleBuilder(
        event_bus=event_bus,
    )

    candle_scheduler = CandleScheduler(
        timeframe=CandleTimeframe.FIVE_MINUTES,
        on_boundary=candle_builder.finalize_interval,
    )

    # =========================================================
    # Indicator System
    # =========================================================

    indicator_state_store = IndicatorStateStore()

    tv_datafeed = TvDatafeed()

    historical_provider = TvDatafeedHistoricalProvider(
        tv_datafeed=tv_datafeed,
    )

    indicator_engine = IndicatorEngine(
        event_bus=event_bus,
        symbol_provider=subscription_registry,
        historical_provider=historical_provider,
        state_store=indicator_state_store,
    )


    # =====================================================
    # Strategy Signal Distribution System
    # =====================================================

    signal_delivery = LogSignalDelivery()

    signal_distributor = SignalDistributor(
        event_bus=event_bus,
        subscription_registry=strategy_user_registry,
        delivery=signal_delivery,
    )


    # =========================================================
    # Strategy System
    # =========================================================

    strategy_factory = StrategyFactory()

    strategy_correlator = StrategyCorrelator()

    strategy_dispatcher = StrategyDispatcher()

    strategy_engine = StrategyEngine(
        event_bus=event_bus,
        correlator=strategy_correlator,
        dispatcher=strategy_dispatcher,
        strategy_registry=strategy_registry,
        strategy_factory=strategy_factory,
    )


    # =====================================================
    # Application Container
    # =====================================================

    return {
        # Core infrastructure
        "event_bus": event_bus,

        # Market session management
        "market_calendar": market_calendar,
        "market_scheduler": market_scheduler,
        "market_session_manager": market_session_manager,

        # Runtime registries
        "subscription_registry": subscription_registry,
        "strategy_registry": strategy_registry,
        "strategy_user_registry": strategy_user_registry,

        # Persistent data access
        "user_session_repository": user_session_repository,

        # Application services
        "session_manager": session_manager,
        "market_data_manager": market_data_manager,

        # Broker / market data
        "authenticator": authenticator,
        "instrument_master": instrument_master,
        "websocket_client": websocket_client,

        # Runtime data pipeline
        "tick_cache": tick_cache,
        "candle_builder": candle_builder,
        "candle_scheduler": candle_scheduler,

        # Indicator system
        "indicator_state_store": indicator_state_store,
        "historical_provider": historical_provider,
        "indicator_engine": indicator_engine,
        
        # Strategy system
        "strategy_correlator": strategy_correlator,
        "strategy_dispatcher": strategy_dispatcher,
        "strategy_engine": strategy_engine,
        "strategy_factory": strategy_factory,

        # Signal distribution
        "signal_delivery": signal_delivery,
        "signal_distributor": signal_distributor,
    }


def main() -> None:
    """
    Start the trading engine application.

    Application construction and dependency wiring are handled
    by build_application(). Runtime startup and lifecycle
    management will be handled here.
    """

    application = build_application()

    # Start the application lifecycle.
   

    # Component startup order will be defined here once
    application["market_data_manager"].start()
    application["tick_cache"].start()
    application["candle_builder"].start()
    application["candle_scheduler"].start()
    application["indicator_engine"].start()
    application["strategy_engine"].start()
    application["signal_distributor"].start()
    application["session_manager"].start()
    application["market_session_manager"].start()

    # This is only for our current development/testing stage.
    input("Trading engine is running. Press Enter to stop...\n")
    # all runtime components have been wired.


if __name__ == "__main__":
    main()