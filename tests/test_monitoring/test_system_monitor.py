from candle.candle_models import CandleBatch
from event_system.event import Event
from event_system.event_bus import EventBus
from event_system.event_type import EventType
from indicators.indicator_models import IndicatorBatch
from monitoring.system_monitor import SystemMonitor


from datetime import datetime
from unittest.mock import Mock

from market_data.market_data_manager import MarketDataManager
from market_data.models import Tick
from registry.subscription_registry import SubscriptionRegistry

from datetime import datetime

from strategy.strategy_models import StrategyGroup
from strategy.strategy_output import (
    StrategyOutput,
    SignalType,
    SignalSide,
)

def test_market_open_updates_monitor():
    # Create the EventBus.
    # The EventBus is responsible for delivering events
    # to all components that subscribed to them.
    event_bus = EventBus()

    # Create the SystemMonitor and give it the EventBus.
    # SystemMonitor subscribes to MARKET_OPEN and MARKET_CLOSE
    # events during initialization.
    monitor = SystemMonitor(event_bus)

    # Simulate the real application publishing a MARKET_OPEN event.
    # In the real system, MarketSessionManager will publish this event.
    event_bus.publish(
        Event(event_type=EventType.MARKET_OPEN)
    )

    # Ask the monitor for its current monitoring state.
    snapshot = monitor.get_snapshot()

    # MARKET_OPEN should have been received by SystemMonitor,
    # which should update the market state from its event handler.
    assert snapshot["system"]["market_state"] == "OPEN"


def test_market_close_updates_monitor():
    # Create a fresh EventBus for this test.
    event_bus = EventBus()

    # Create a fresh SystemMonitor.
    # It subscribes to MARKET_OPEN and MARKET_CLOSE.
    monitor = SystemMonitor(event_bus)

    # Simulate the real application publishing a MARKET_CLOSE event.
    # In the real system, MarketSessionManager will publish this event.
    event_bus.publish(
        Event(event_type=EventType.MARKET_CLOSE)
    )

    # Read the state maintained by the monitor.
    snapshot = monitor.get_snapshot()

    # MARKET_CLOSE should have been received by SystemMonitor,
    # so the market state should now be CLOSED.
    assert snapshot["system"]["market_state"] == "CLOSED"


def test_active_symbols():
    # Create the EventBus used by the SystemMonitor.
    event_bus = EventBus()

    # Create the central monitoring component.
    monitor = SystemMonitor(event_bus)

    # Simulate MarketDataManager reporting
    # the number of currently subscribed symbols.
    monitor.update_active_symbols(5)

    # Read the current monitoring snapshot.
    snapshot = monitor.get_snapshot()

    # The monitor should expose the reported active-symbol count.
    assert snapshot["market_data"]["active_symbols"] == 5


def test_record_tick():
    # Create the EventBus used by the SystemMonitor.
    event_bus = EventBus()

    # Create the central monitoring component.
    monitor = SystemMonitor(event_bus)

    # Simulate one accepted market tick.
    monitor.record_tick()

    # Simulate another accepted market tick.
    monitor.record_tick()

    # Read the current monitoring snapshot.
    snapshot = monitor.get_snapshot()

    # The monitor should report both accepted ticks.
    assert snapshot["market_data"]["ticks_received"] == 2


def test_market_data_manager_records_accepted_tick():
    # Create the EventBus used by both components.
    event_bus = EventBus()

    # Create the central monitoring component.
    monitor = SystemMonitor(event_bus)

    # Create a fake WebSocket client.
    # The real broker WebSocket is not needed for this test.
    websocket_client = Mock()

    # Create the SubscriptionRegistry required by MarketDataManager.
    subscription_registry = SubscriptionRegistry()

    # Create MarketDataManager with the real monitoring component.
    manager = MarketDataManager(
        event_bus=event_bus,
        subscription_registry=subscription_registry,
        websocket_client=websocket_client,
        system_monitor=monitor,
    )

    # Simulate the market-data pipeline currently accepting ticks.
    manager._accepting_ticks = True

    # Create one fake market tick.
    tick = Tick(
        symbol="NIFTY",
        price=100.0,
        timestamp=datetime.now(),
    )

    # Simulate the WebSocket delivering the tick to MarketDataManager.
    manager._on_tick(tick)

    # Read the monitoring state.
    snapshot = monitor.get_snapshot()

    # The accepted tick should have been counted.
    assert snapshot["market_data"]["ticks_received"] == 1


def test_market_data_manager_does_not_record_rejected_tick():
    # Create the EventBus used by both components.
    event_bus = EventBus()

    # Create the central monitoring component.
    monitor = SystemMonitor(event_bus)

    # Create a fake WebSocket client.
    websocket_client = Mock()

    # Create the subscription registry required by MarketDataManager.
    subscription_registry = SubscriptionRegistry()

    # Create MarketDataManager with the central monitor.
    manager = MarketDataManager(
        event_bus=event_bus,
        subscription_registry=subscription_registry,
        websocket_client=websocket_client,
        system_monitor=monitor,
    )

    # Simulate the market-data pipeline NOT accepting ticks.
    # This is the state after MARKET_CLOSE.
    manager._accepting_ticks = False

    # Create a tick that arrives after the pipeline stopped accepting ticks.
    tick = Tick(
        symbol="NIFTY",
        price=100.0,
        timestamp=datetime.now(),
    )

    # Simulate the WebSocket delivering this late tick.
    manager._on_tick(tick)

    # Read the monitoring state.
    snapshot = monitor.get_snapshot()

    # The rejected tick must NOT be counted.
    assert snapshot["market_data"].get("ticks_received", 0) == 0


def test_market_data_manager_updates_active_symbols():
    # Create the EventBus shared by the components.
    event_bus = EventBus()

    # Create the central monitoring component.
    monitor = SystemMonitor(event_bus)

    # Create the registry that stores symbols required by active sessions.
    subscription_registry = SubscriptionRegistry()

    # Add the symbols that MarketDataManager should subscribe to.
    subscription_registry.add_symbol("NIFTY")
    subscription_registry.add_symbol("BANKNIFTY")
    subscription_registry.add_symbol("RELIANCE")

    # Create a fake WebSocket client.
    # We only want to test MarketDataManager's subscription logic.
    websocket_client = Mock()

    # Create MarketDataManager with the real monitoring component.
    manager = MarketDataManager(
        event_bus=event_bus,
        subscription_registry=subscription_registry,
        websocket_client=websocket_client,
        system_monitor=monitor,
    )

    # Synchronize MarketDataManager with the SubscriptionRegistry.
    manager._sync_subscriptions()

    # Read the monitoring state.
    snapshot = monitor.get_snapshot()

    # The monitor should report the number of symbols
    # that MarketDataManager actually subscribed to.
    assert snapshot["market_data"]["active_symbols"] == 3


def test_record_candle_by_symbol_and_timeframe():
    # Create the EventBus used by the SystemMonitor.
    event_bus = EventBus()

    # Create the central monitoring component.
    monitor = SystemMonitor(event_bus)

    # Simulate two completed 5-minute candles for NIFTY.
    monitor.record_candle("NIFTY", "5m")
    monitor.record_candle("NIFTY", "5m")

    # Simulate one completed 5-minute candle for BANKNIFTY.
    monitor.record_candle("BANKNIFTY", "5m")

    # Simulate one completed 15-minute candle for NIFTY.
    monitor.record_candle("NIFTY", "15m")

    # Read the current monitoring snapshot.
    snapshot = monitor.get_snapshot()

    # Each symbol/timeframe combination should have
    # its own independent completed-candle count.
    assert snapshot["candles"][("NIFTY", "5m")] == 2
    assert snapshot["candles"][("BANKNIFTY", "5m")] == 1
    assert snapshot["candles"][("NIFTY", "15m")] == 1


def test_candle_batch_updates_monitor():
    # Create the EventBus used by the monitor.
    event_bus = EventBus()

    # Create the central monitoring component.
    monitor = SystemMonitor(event_bus)

    # Publish a completed candle batch.
    batch = CandleBatch(
        timeframe="5m",
        start_time=...,
        end_time=...,
        candles={
            "NIFTY": ...,
            "BANKNIFTY": ...,
        },
    )

    event_bus.publish(
        Event(
            event_type=EventType.CANDLE_BATCH_CLOSED,
            payload=batch,
        )
    )

    snapshot = monitor.get_snapshot()

    # Both symbols produced one completed 5m candle.
    assert snapshot["candles"][("NIFTY", "5m")] == 1
    assert snapshot["candles"][("BANKNIFTY", "5m")] == 1


def test_indicator_batch_updates_monitor():
    # Create the EventBus used by the monitor.
    event_bus = EventBus()

    # Create the central monitoring component.
    monitor = SystemMonitor(event_bus)

    # Create indicator results for two active symbols.
    batch = IndicatorBatch(
        timeframe="5m",
        start_time=...,
        end_time=...,
        indicators={
            "NIFTY": ...,
            "BANKNIFTY": ...,
        },
    )

    # Simulate the event that the IndicatorEngine publishes
    # after calculating indicators for the completed candle batch.
    event_bus.publish(
        Event(
            event_type=EventType.INDICATOR_BATCH_UPDATED,
            payload=batch,
        )
    )

    snapshot = monitor.get_snapshot()

    # Two symbols produced indicator results on the 5m timeframe.
    assert snapshot["indicators"]["5m"] == 2


def test_strategy_signal_updates_monitor():
    # Create the EventBus used by the monitor.
    event_bus = EventBus()

    # Create the central monitoring component.
    monitor = SystemMonitor(event_bus)

    strategy_group = StrategyGroup(
        strategy_type="EMA",
        symbol="NIFTY",
        timeframe="5m",
        parameters=(("period", 10),),
    )

    output = StrategyOutput(
        strategy_group=strategy_group,
        signal_type=SignalType.ENTRY,
        side=SignalSide.BUY,
        timestamp=datetime.now(),
    )

    # Simulate the event published by StrategyEngine
    # after the strategy produces a decision.
    event_bus.publish(
        Event(
            event_type=EventType.STRATEGY_SIGNAL_GENERATED,
            payload=output,
        )
    )

    snapshot = monitor.get_snapshot()

    # One EMA strategy signal was generated.
    assert snapshot["strategies"]["EMA"]["signals"] == 1


def test_signal_distribution_updates_monitor():
    event_bus = EventBus()
    monitor = SystemMonitor(event_bus)

    # Publish one signal received event
    event_bus.publish(
        Event(
            event_type=EventType.SIGNAL_RECEIVED,
            payload=None,
        )
    )

    # Publish one signal distributed event
    event_bus.publish(
        Event(
            event_type=EventType.SIGNAL_DISTRIBUTED,
            payload=None,
        )
    )

    snapshot = monitor.get_snapshot()

    assert snapshot["signal_distribution"]["signals_received"] == 1
    assert snapshot["signal_distribution"]["signals_distributed"] == 1

