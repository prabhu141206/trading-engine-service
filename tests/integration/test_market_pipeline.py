from datetime import datetime
from unittest.mock import Mock

from candle.candle_builder import CandleBuilder
from candle.candle_scheduler import CandleScheduler
from candle.candle_timeframe import CandleTimeframe
from event_system.event import Event
from event_system.event_bus import EventBus
from event_system.event_type import EventType
from market_data.fake_websocket_client import FakeWebSocketClient
from market_data.market_data_manager import MarketDataManager
from market_data.models import Tick
from registry.subscription_registry import SubscriptionRegistry

from indicators.indicator_state import IndicatorStateStore
from indicators.indicator_models import IndicatorBatch, SymbolIndicatorState
from registry.strategy_registry import StrategyRegistry
from strategy.strategy_correlator import StrategyCorrelator
from strategy.strategy_dispatcher import StrategyDispatcher
from strategy.strategy_engine import StrategyEngine
from strategy.strategy_factory import StrategyFactory
from strategy.strategy_models import StrategyGroup

from registry.strategy_user_registry import StrategyUserRegistry
from signal_distribution.signal_delivery import SignalDelivery
from signal_distribution.signal_distributor import SignalDistributor
from strategy.strategy_output import (
    SignalSide,
    SignalType,
    StrategyOutput,
)


from indicators.fake_active_symbol_provider import FakeActiveSymbolProvider
from indicators.fake_historical_data_provider import FakeHistoricalCandleProvider
from indicators.indicator_engine import IndicatorEngine
from indicators.indicator_state import IndicatorStateStore
from registry.strategy_registry import StrategyRegistry
from registry.strategy_user_registry import StrategyUserRegistry
from signal_distribution.signal_delivery import SignalDelivery
from signal_distribution.signal_distributor import SignalDistributor
from strategy.strategy_correlator import StrategyCorrelator
from strategy.strategy_dispatcher import StrategyDispatcher
from strategy.strategy_engine import StrategyEngine
from strategy.strategy_factory import StrategyFactory
from strategy.strategy_models import StrategyGroup


## Scenario 1 — Tick to Candle
def test_market_data_to_candle_pipeline():
    # ---------------------------------------------------------
    # Setup
    # ---------------------------------------------------------

    event_bus = EventBus()
    subscription_registry = SubscriptionRegistry()
    websocket = FakeWebSocketClient()
    system_monitor = Mock()

    subscription_registry.add_symbol("NIFTY")

    candle_batches = []

    event_bus.subscribe(
        EventType.CANDLE_BATCH_CLOSED,
        lambda event: candle_batches.append(event.payload),
    )

    market_data_manager = MarketDataManager(
        event_bus=event_bus,
        subscription_registry=subscription_registry,
        websocket_client=websocket,
        system_monitor=system_monitor,
    )

    candle_builder = CandleBuilder(
        event_bus=event_bus,
    )

    candle_scheduler = CandleScheduler(
        timeframe=CandleTimeframe.FIVE_MINUTES,
        on_boundary=candle_builder.finalize_interval,
    )

    # ---------------------------------------------------------
    # Start
    # ---------------------------------------------------------

    market_data_manager.start()
    candle_builder.start()

    # Session configuration is ready.
    event_bus.publish(
        Event(
            event_type=EventType.SESSIONS_READY,
        )
    )

    # ---------------------------------------------------------
    # Feed market ticks
    # ---------------------------------------------------------

    websocket.emit_tick(
        Tick(
            symbol="NIFTY",
            price=100.0,
            timestamp=datetime(2026, 10, 8, 10, 15, 10),
        )
    )

    websocket.emit_tick(
        Tick(
            symbol="NIFTY",
            price=105.0,
            timestamp=datetime(2026, 10, 8, 10, 16, 20),
        )
    )

    websocket.emit_tick(
        Tick(
            symbol="NIFTY",
            price=98.0,
            timestamp=datetime(2026, 10, 8, 10, 18, 30),
        )
    )

    websocket.emit_tick(
        Tick(
            symbol="NIFTY",
            price=103.0,
            timestamp=datetime(2026, 10, 8, 10, 19, 50),
        )
    )

    # ---------------------------------------------------------
    # Finalize 10:15 -> 10:20 candle
    # ---------------------------------------------------------

    candle_scheduler.trigger_boundary(
        datetime(2026, 10, 8, 10, 20, 0)
    )

    # ---------------------------------------------------------
    # Assertions
    # ---------------------------------------------------------

    assert len(candle_batches) == 1

    batch = candle_batches[0]

    assert batch.timeframe == CandleTimeframe.FIVE_MINUTES.value
    assert batch.start_time == datetime(2026, 10, 8, 10, 15, 0)
    assert batch.end_time == datetime(2026, 10, 8, 10, 20, 0)

    candle = batch.candles["NIFTY"]

    assert candle.open == 100.0
    assert candle.high == 105.0
    assert candle.low == 98.0
    assert candle.close == 103.0


from candle.candle_models import Candle, CandleBatch
from indicators.fake_active_symbol_provider import FakeActiveSymbolProvider
from indicators.fake_historical_data_provider import FakeHistoricalCandleProvider
from indicators.indicator_engine import IndicatorEngine
from indicators.indicator_state import IndicatorStateStore


def test_candle_to_indicator_pipeline():
    # ---------------------------------------------------------
    # Setup
    # ---------------------------------------------------------

    event_bus = EventBus()
    state_store = IndicatorStateStore()

    historical_candles = [
        Candle(
            symbol="NIFTY",
            timeframe="5m",
            start_time=None,
            end_time=None,
            open=float(close),
            high=float(close),
            low=float(close),
            close=float(close),
        )
        for close in range(90, 140)
    ]

    symbol_provider = FakeActiveSymbolProvider(
        symbols=["NIFTY"],
    )

    historical_provider = FakeHistoricalCandleProvider(
        candles_by_symbol={
            "NIFTY": historical_candles,
        }
    )

    indicator_engine = IndicatorEngine(
        event_bus=event_bus,
        symbol_provider=symbol_provider,
        historical_provider=historical_provider,
        state_store=state_store,
    )

    indicator_batches = []

    event_bus.subscribe(
        EventType.INDICATOR_BATCH_UPDATED,
        lambda event: indicator_batches.append(event.payload),
    )

    # ---------------------------------------------------------
    # Start
    # ---------------------------------------------------------

    indicator_engine.start()

    # Trigger the real IndicatorEngine warm-up lifecycle.
    event_bus.publish(
        Event(
            event_type=EventType.SESSIONS_READY,
        )
    )

    # Wait for the real warm-up thread to finish.
    indicator_engine._warmup_thread.join()

    # ---------------------------------------------------------
    # Verify warm-up
    # ---------------------------------------------------------

    state_before = state_store.get(
        symbol="NIFTY",
        timeframe="5m",
    )

    assert state_before is not None
    assert state_before.ready is True

    ema_before = state_before.ema_10

    # ---------------------------------------------------------
    # Publish completed candle
    # ---------------------------------------------------------

    candle = Candle(
        symbol="NIFTY",
        timeframe="5m",
        start_time=datetime(2026, 10, 8, 10, 15),
        end_time=datetime(2026, 10, 8, 10, 20),
        open=140.0,
        high=145.0,
        low=138.0,
        close=142.0,
    )

    batch = CandleBatch(
        timeframe="5m",
        start_time=datetime(2026, 10, 8, 10, 15),
        end_time=datetime(2026, 10, 8, 10, 20),
        candles={
            "NIFTY": candle,
        },
    )

    event_bus.publish(
        Event(
            event_type=EventType.CANDLE_BATCH_CLOSED,
            payload=batch,
        )
    )

    # ---------------------------------------------------------
    # Assertions
    # ---------------------------------------------------------

    state_after = state_store.get(
        symbol="NIFTY",
        timeframe="5m",
    )

    assert state_after is not None
    assert state_after.ready is True
    assert state_after.ema_10 != ema_before

    assert len(indicator_batches) == 1

    indicator_batch = indicator_batches[0]

    assert indicator_batch.timeframe == "5m"
    assert indicator_batch.start_time == datetime(
        2026, 10, 8, 10, 15
    )
    assert indicator_batch.end_time == datetime(
        2026, 10, 8, 10, 20
    )

    assert "NIFTY" in indicator_batch.indicators



## Scenario 3 — Candle + Indicator to Strategy
def test_candle_and_indicator_to_strategy_pipeline():
    # ---------------------------------------------------------
    # Setup
    # ---------------------------------------------------------

    event_bus = EventBus()

    strategy_registry = StrategyRegistry()

    strategy_registry.add_group(
        StrategyGroup(
            strategy_type="EMA",
            symbol="NIFTY",
            timeframe="5m",
            parameters=(("period", 10),),
        )
    )

    correlator = StrategyCorrelator()
    dispatcher = StrategyDispatcher()
    strategy_factory = StrategyFactory()

    strategy_engine = StrategyEngine(
        event_bus=event_bus,
        correlator=correlator,
        dispatcher=dispatcher,
        strategy_registry=strategy_registry,
        strategy_factory=strategy_factory,
    )

    signals = []

    event_bus.subscribe(
        EventType.STRATEGY_SIGNAL_GENERATED,
        lambda event: signals.append(event.payload),
    )

    # ---------------------------------------------------------
    # Start
    # ---------------------------------------------------------

    strategy_engine.start()

    # Create the real EMA strategy from the registered
    # strategy group.
    event_bus.publish(
        Event(
            event_type=EventType.SESSIONS_READY,
        )
    )

    # ---------------------------------------------------------
    # Create matching candle + indicator
    # ---------------------------------------------------------

    candle = Candle(
        symbol="NIFTY",
        timeframe="5m",
        start_time=datetime(2026, 10, 8, 10, 15),
        end_time=datetime(2026, 10, 8, 10, 20),
        open=105.0,
        high=108.0,
        low=103.0,
        close=104.0,
    )

    candle_batch = CandleBatch(
        timeframe="5m",
        start_time=candle.start_time,
        end_time=candle.end_time,
        candles={
            "NIFTY": candle,
        },
    )

    indicator_batch = IndicatorBatch(
        timeframe="5m",
        start_time=candle.start_time,
        end_time=candle.end_time,
        indicators={
            "NIFTY": SymbolIndicatorState(
                symbol="NIFTY",
                timeframe="5m",
                ema_10=100.0,
                ready=True,
            ),
        },
    )

    # ---------------------------------------------------------
    # Candle arrives first
    # ---------------------------------------------------------

    event_bus.publish(
        Event(
            event_type=EventType.CANDLE_BATCH_CLOSED,
            payload=candle_batch,
        )
    )

    # The correlator has the candle, but no matching indicator yet.
    assert signals == []

    # ---------------------------------------------------------
    # Matching indicator arrives
    # ---------------------------------------------------------

    event_bus.publish(
        Event(
            event_type=EventType.INDICATOR_BATCH_UPDATED,
            payload=indicator_batch,
        )
    )

    # The matching candle + indicator should arm the EMA strategy.
    # No signal is generated yet because the trigger has not broken.
    assert signals == []

    # ---------------------------------------------------------
    # Tick breaks trigger candle high
    # ---------------------------------------------------------

    event_bus.publish(
        Event(
            event_type=EventType.TICK_RECEIVED,
            payload=Tick(
                symbol="NIFTY",
                price=108.1,
                timestamp=datetime(2026, 10, 8, 10, 20),
            ),
        )
    )

    # ---------------------------------------------------------
    # Assertions
    # ---------------------------------------------------------

    assert len(signals) == 1

    signal = signals[0]

    assert signal.strategy_group.strategy_type == "EMA"
    assert signal.strategy_group.symbol == "NIFTY"
    assert signal.strategy_group.timeframe == "5m"
    assert signal.strategy_group.parameters == (("period", 10),)

    assert signal.signal_type is SignalType.ENTRY
    assert signal.side is SignalSide.BUY


## Scenario 4 — Strategy Signal Distribution
def test_strategy_signal_distribution_pipeline():
    # ---------------------------------------------------------
    # Setup
    # ---------------------------------------------------------

    event_bus = EventBus()
    subscription_registry = StrategyUserRegistry()

    strategy_group = StrategyGroup(
        strategy_type="EMA",
        symbol="NIFTY",
        timeframe="5m",
        parameters=(("period", 10),),
    )

    # ---------------------------------------------------------
    # Test delivery boundary
    # ---------------------------------------------------------

    class RecordingDelivery(SignalDelivery):
        def __init__(self):
            self.deliveries = []

        def deliver(
            self,
            user_id: int,
            signal,
        ) -> None:
            self.deliveries.append(
                (user_id, signal)
            )

    delivery = RecordingDelivery()

    # ---------------------------------------------------------
    # Register subscribers
    # ---------------------------------------------------------

    subscription_registry.subscribe(
        user_id=101,
        group=strategy_group,
    )

    subscription_registry.subscribe(
        user_id=202,
        group=strategy_group,
    )

    subscription_registry.subscribe(
        user_id=303,
        group=strategy_group,
    )

    # This user belongs to a different strategy group.
    unrelated_group = StrategyGroup(
        strategy_type="EMA",
        symbol="BANKNIFTY",
        timeframe="5m",
        parameters=(("period", 10),),
    )

    subscription_registry.subscribe(
        user_id=404,
        group=unrelated_group,
    )

    # ---------------------------------------------------------
    # Create distributor
    # ---------------------------------------------------------

    distributor = SignalDistributor(
        event_bus=event_bus,
        subscription_registry=subscription_registry,
        delivery=delivery,
    )

    received_signals = []
    distributed_signals = []

    event_bus.subscribe(
        EventType.SIGNAL_RECEIVED,
        lambda event: received_signals.append(
            event.payload
        ),
    )

    event_bus.subscribe(
        EventType.SIGNAL_DISTRIBUTED,
        lambda event: distributed_signals.append(
            event.payload
        ),
    )

    distributor.start()

    # ---------------------------------------------------------
    # Create generated strategy signal
    # ---------------------------------------------------------

    signal = StrategyOutput(
        strategy_group=strategy_group,
        signal_type=SignalType.ENTRY,
        side=SignalSide.BUY,
        timestamp=datetime(2026, 10, 8, 10, 20),
    )

    # ---------------------------------------------------------
    # Publish through the real EventBus
    # ---------------------------------------------------------

    event_bus.publish(
        Event(
            event_type=EventType.STRATEGY_SIGNAL_GENERATED,
            payload=signal,
        )
    )

    # ---------------------------------------------------------
    # Assertions
    # ---------------------------------------------------------

    # One generated signal entered distribution.
    assert len(received_signals) == 1
    assert received_signals[0] is signal

    # Exactly three subscribed users received it.
    assert len(delivery.deliveries) == 3

    delivered_user_ids = {
        user_id
        for user_id, delivered_signal
        in delivery.deliveries
    }

    assert delivered_user_ids == {
        101,
        202,
        303,
    }

    # Every delivery received the exact same signal.
    for _, delivered_signal in delivery.deliveries:
        assert delivered_signal is signal

    # One distribution event per successful delivery.
    assert len(distributed_signals) == 3

    for distributed_signal in distributed_signals:
        assert distributed_signal is signal



## Scenario 5 — Complete Market Pipeline
def test_complete_market_pipeline():
    # ---------------------------------------------------------
    # Setup
    # ---------------------------------------------------------

    event_bus = EventBus()

    # ---------------------------------------------------------
    # Market data
    # ---------------------------------------------------------

    subscription_registry = SubscriptionRegistry()
    subscription_registry.add_symbol("NIFTY")

    websocket = FakeWebSocketClient()
    system_monitor = Mock()

    market_data_manager = MarketDataManager(
        event_bus=event_bus,
        subscription_registry=subscription_registry,
        websocket_client=websocket,
        system_monitor=system_monitor,
    )

    # ---------------------------------------------------------
    # Candle
    # ---------------------------------------------------------

    candle_builder = CandleBuilder(
        event_bus=event_bus,
    )

    candle_scheduler = CandleScheduler(
        timeframe=CandleTimeframe.FIVE_MINUTES,
        on_boundary=candle_builder.finalize_interval,
    )

    # ---------------------------------------------------------
    # Indicator
    # ---------------------------------------------------------

    historical_candles = [
        Candle(
            symbol="NIFTY",
            timeframe="5m",
            start_time=None,
            end_time=None,
            open=float(close),
            high=float(close),
            low=float(close),
            close=float(close),
        )
        for close in range(90, 140)
    ]

    symbol_provider = FakeActiveSymbolProvider(
        symbols=["NIFTY"],
    )

    historical_provider = FakeHistoricalCandleProvider(
        candles_by_symbol={
            "NIFTY": historical_candles,
        }
    )

    indicator_state_store = IndicatorStateStore()

    indicator_engine = IndicatorEngine(
        event_bus=event_bus,
        symbol_provider=symbol_provider,
        historical_provider=historical_provider,
        state_store=indicator_state_store,
    )

    # ---------------------------------------------------------
    # Strategy
    # ---------------------------------------------------------

    strategy_group = StrategyGroup(
        strategy_type="EMA",
        symbol="NIFTY",
        timeframe="5m",
        parameters=(("period", 10),),
    )

    strategy_registry = StrategyRegistry()

    strategy_registry.add_group(
        strategy_group
    )

    strategy_engine = StrategyEngine(
        event_bus=event_bus,
        correlator=StrategyCorrelator(),
        dispatcher=StrategyDispatcher(),
        strategy_registry=strategy_registry,
        strategy_factory=StrategyFactory(),
    )

    # ---------------------------------------------------------
    # Signal distribution
    # ---------------------------------------------------------

    strategy_user_registry = StrategyUserRegistry()

    strategy_user_registry.subscribe(
        user_id=101,
        group=strategy_group,
    )

    class RecordingDelivery(SignalDelivery):
        def __init__(self):
            self.deliveries = []

        def deliver(
            self,
            user_id: int,
            signal,
        ) -> None:
            self.deliveries.append(
                (user_id, signal)
            )

    delivery = RecordingDelivery()

    signal_distributor = SignalDistributor(
        event_bus=event_bus,
        subscription_registry=strategy_user_registry,
        delivery=delivery,
    )

    # ---------------------------------------------------------
    # Start production components
    # ---------------------------------------------------------

    market_data_manager.start()
    candle_builder.start()
    indicator_engine.start()
    strategy_engine.start()
    signal_distributor.start()

    # ---------------------------------------------------------
    # Start market session
    # ---------------------------------------------------------

    event_bus.publish(
        Event(
            event_type=EventType.SESSIONS_READY,
        )
    )

    # Indicator warm-up happens in a background thread.
    indicator_engine._warmup_thread.join()

    # ---------------------------------------------------------
    # Feed actual market ticks
    # ---------------------------------------------------------

    websocket.emit_tick(
        Tick(
            symbol="NIFTY",
            price=150.0,
            timestamp=datetime(2026, 10, 8, 10, 15, 10),
        )
    )

    websocket.emit_tick(
        Tick(
            symbol="NIFTY",
            price=152.0,
            timestamp=datetime(2026, 10, 8, 10, 16, 20),
        )
    )

    websocket.emit_tick(
        Tick(
            symbol="NIFTY",
            price=149.0,
            timestamp=datetime(2026, 10, 8, 10, 18, 30),
        )
    )

    websocket.emit_tick(
        Tick(
            symbol="NIFTY",
            price=148.0,
            timestamp=datetime(2026, 10, 8, 10, 19, 50),
        )
    )

    # ---------------------------------------------------------
    # Finalize the real candle
    # ---------------------------------------------------------

    candle_scheduler.trigger_boundary(
        datetime(2026, 10, 8, 10, 20, 0)
    )

    # ---------------------------------------------------------
    # Break the EMA strategy trigger
    # ---------------------------------------------------------

    websocket.emit_tick(
        Tick(
            symbol="NIFTY",
            price=152.1,
            timestamp=datetime(2026, 10, 8, 10, 20, 10),
        )
    )

    # ---------------------------------------------------------
    # Assertions
    # ---------------------------------------------------------

    assert len(delivery.deliveries) == 1

    user_id, signal = delivery.deliveries[0]

    assert user_id == 101

    assert signal.strategy_group == strategy_group
    assert signal.signal_type is SignalType.ENTRY
    assert signal.side is SignalSide.BUY


## Scenario 6 — Multiple Symbols
def test_multiple_symbols_market_pipeline():
    # ---------------------------------------------------------
    # Setup
    # ---------------------------------------------------------

    event_bus = EventBus()

    # ---------------------------------------------------------
    # Market data
    # ---------------------------------------------------------

    subscription_registry = SubscriptionRegistry()
    subscription_registry.add_symbol("NIFTY")
    subscription_registry.add_symbol("BANKNIFTY")

    websocket = FakeWebSocketClient()
    system_monitor = Mock()

    market_data_manager = MarketDataManager(
        event_bus=event_bus,
        subscription_registry=subscription_registry,
        websocket_client=websocket,
        system_monitor=system_monitor,
    )

    # ---------------------------------------------------------
    # Candle
    # ---------------------------------------------------------

    candle_builder = CandleBuilder(
        event_bus=event_bus,
    )

    candle_scheduler = CandleScheduler(
        timeframe=CandleTimeframe.FIVE_MINUTES,
        on_boundary=candle_builder.finalize_interval,
    )

    # ---------------------------------------------------------
    # Historical data for both symbols
    # ---------------------------------------------------------

    historical_candles = {
        symbol: [
            Candle(
                symbol=symbol,
                timeframe="5m",
                start_time=None,
                end_time=None,
                open=float(close),
                high=float(close),
                low=float(close),
                close=float(close),
            )
            for close in range(90, 140)
        ]
        for symbol in ("NIFTY", "BANKNIFTY")
    }

    symbol_provider = FakeActiveSymbolProvider(
        symbols=["NIFTY", "BANKNIFTY"],
    )

    historical_provider = FakeHistoricalCandleProvider(
        candles_by_symbol=historical_candles,
    )

    indicator_state_store = IndicatorStateStore()

    indicator_engine = IndicatorEngine(
        event_bus=event_bus,
        symbol_provider=symbol_provider,
        historical_provider=historical_provider,
        state_store=indicator_state_store,
    )

    # ---------------------------------------------------------
    # Strategy
    # ---------------------------------------------------------

    nifty_group = StrategyGroup(
        strategy_type="EMA",
        symbol="NIFTY",
        timeframe="5m",
        parameters=(("period", 10),),
    )

    banknifty_group = StrategyGroup(
        strategy_type="EMA",
        symbol="BANKNIFTY",
        timeframe="5m",
        parameters=(("period", 10),),
    )

    strategy_registry = StrategyRegistry()

    strategy_registry.add_group(nifty_group)
    strategy_registry.add_group(banknifty_group)

    strategy_engine = StrategyEngine(
        event_bus=event_bus,
        correlator=StrategyCorrelator(),
        dispatcher=StrategyDispatcher(),
        strategy_registry=strategy_registry,
        strategy_factory=StrategyFactory(),
    )

    # ---------------------------------------------------------
    # Signal distribution
    # ---------------------------------------------------------

    strategy_user_registry = StrategyUserRegistry()

    strategy_user_registry.subscribe(
        user_id=101,
        group=nifty_group,
    )

    strategy_user_registry.subscribe(
        user_id=202,
        group=banknifty_group,
    )

    class RecordingDelivery(SignalDelivery):
        def __init__(self):
            self.deliveries = []

        def deliver(
            self,
            user_id: int,
            signal,
        ) -> None:
            self.deliveries.append(
                (user_id, signal)
            )

    delivery = RecordingDelivery()

    signal_distributor = SignalDistributor(
        event_bus=event_bus,
        subscription_registry=strategy_user_registry,
        delivery=delivery,
    )

    # ---------------------------------------------------------
    # Start production components
    # ---------------------------------------------------------

    market_data_manager.start()
    candle_builder.start()
    indicator_engine.start()
    strategy_engine.start()
    signal_distributor.start()

    # ---------------------------------------------------------
    # Start session
    # ---------------------------------------------------------

    event_bus.publish(
        Event(
            event_type=EventType.SESSIONS_READY,
        )
    )

    indicator_engine._warmup_thread.join()

    # ---------------------------------------------------------
    # Feed NIFTY ticks
    # ---------------------------------------------------------

    websocket.emit_tick(
        Tick(
            symbol="NIFTY",
            price=150.0,
            timestamp=datetime(2026, 10, 8, 10, 15, 10),
        )
    )

    websocket.emit_tick(
        Tick(
            symbol="NIFTY",
            price=152.0,
            timestamp=datetime(2026, 10, 8, 10, 16, 20),
        )
    )

    websocket.emit_tick(
        Tick(
            symbol="NIFTY",
            price=149.0,
            timestamp=datetime(2026, 10, 8, 10, 18, 30),
        )
    )

    websocket.emit_tick(
        Tick(
            symbol="NIFTY",
            price=148.0,
            timestamp=datetime(2026, 10, 8, 10, 19, 50),
        )
    )

    # ---------------------------------------------------------
    # Feed BANKNIFTY ticks
    # ---------------------------------------------------------

    websocket.emit_tick(
        Tick(
            symbol="BANKNIFTY",
            price=250.0,
            timestamp=datetime(2026, 10, 8, 10, 15, 10),
        )
    )

    websocket.emit_tick(
        Tick(
            symbol="BANKNIFTY",
            price=252.0,
            timestamp=datetime(2026, 10, 8, 10, 16, 20),
        )
    )

    websocket.emit_tick(
        Tick(
            symbol="BANKNIFTY",
            price=249.0,
            timestamp=datetime(2026, 10, 8, 10, 18, 30),
        )
    )

    websocket.emit_tick(
        Tick(
            symbol="BANKNIFTY",
            price=248.0,
            timestamp=datetime(2026, 10, 8, 10, 19, 50),
        )
    )

    # ---------------------------------------------------------
    # Finalize the shared 10:15 -> 10:20 interval
    # ---------------------------------------------------------

    candle_scheduler.trigger_boundary(
        datetime(2026, 10, 8, 10, 20, 0)
    )

    # ---------------------------------------------------------
    # Break both strategy triggers
    # ---------------------------------------------------------

    websocket.emit_tick(
        Tick(
            symbol="NIFTY",
            price=152.1,
            timestamp=datetime(2026, 10, 8, 10, 20, 10),
        )
    )

    websocket.emit_tick(
        Tick(
            symbol="BANKNIFTY",
            price=252.1,
            timestamp=datetime(2026, 10, 8, 10, 20, 10),
        )
    )

    # ---------------------------------------------------------
    # Assertions
    # ---------------------------------------------------------

    assert len(delivery.deliveries) == 2

    deliveries_by_user = {
        user_id: signal
        for user_id, signal in delivery.deliveries
    }

    assert set(deliveries_by_user) == {
        101,
        202,
    }

    nifty_signal = deliveries_by_user[101]
    banknifty_signal = deliveries_by_user[202]

    # NIFTY stayed associated with NIFTY.
    assert nifty_signal.strategy_group == nifty_group
    assert nifty_signal.strategy_group.symbol == "NIFTY"
    assert nifty_signal.signal_type is SignalType.ENTRY
    assert nifty_signal.side is SignalSide.BUY

    # BANKNIFTY stayed associated with BANKNIFTY.
    assert banknifty_signal.strategy_group == banknifty_group
    assert banknifty_signal.strategy_group.symbol == "BANKNIFTY"
    assert banknifty_signal.signal_type is SignalType.ENTRY
    assert banknifty_signal.side is SignalSide.BUY


## Scenario 7 — Multiple Strategy Subscribers
def test_multiple_strategy_subscribers():
    # ---------------------------------------------------------
    # Setup
    # ---------------------------------------------------------

    event_bus = EventBus()
    subscription_registry = StrategyUserRegistry()

    strategy_group = StrategyGroup(
        strategy_type="EMA",
        symbol="NIFTY",
        timeframe="5m",
        parameters=(("period", 10),),
    )

    # ---------------------------------------------------------
    # Subscribe multiple users to the same strategy
    # ---------------------------------------------------------

    subscription_registry.subscribe(
        user_id=101,
        group=strategy_group,
    )

    subscription_registry.subscribe(
        user_id=202,
        group=strategy_group,
    )

    subscription_registry.subscribe(
        user_id=303,
        group=strategy_group,
    )

    # ---------------------------------------------------------
    # Recording delivery boundary
    # ---------------------------------------------------------

    class RecordingDelivery(SignalDelivery):
        def __init__(self):
            self.deliveries = []

        def deliver(
            self,
            user_id: int,
            signal: StrategyOutput,
        ) -> None:
            self.deliveries.append(
                (user_id, signal)
            )

    delivery = RecordingDelivery()

    # ---------------------------------------------------------
    # Start real distributor
    # ---------------------------------------------------------

    distributor = SignalDistributor(
        event_bus=event_bus,
        subscription_registry=subscription_registry,
        delivery=delivery,
    )

    received_signals = []
    distributed_signals = []

    event_bus.subscribe(
        EventType.SIGNAL_RECEIVED,
        lambda event: received_signals.append(
            event.payload
        ),
    )

    event_bus.subscribe(
        EventType.SIGNAL_DISTRIBUTED,
        lambda event: distributed_signals.append(
            event.payload
        ),
    )

    distributor.start()

    # ---------------------------------------------------------
    # One strategy signal
    # ---------------------------------------------------------

    signal = StrategyOutput(
        strategy_group=strategy_group,
        signal_type=SignalType.ENTRY,
        side=SignalSide.BUY,
        timestamp=datetime(2026, 10, 8, 10, 20),
    )

    # ---------------------------------------------------------
    # Publish ONE generated strategy signal
    # ---------------------------------------------------------

    event_bus.publish(
        Event(
            event_type=EventType.STRATEGY_SIGNAL_GENERATED,
            payload=signal,
        )
    )

    # ---------------------------------------------------------
    # Verify
    # ---------------------------------------------------------

    # Exactly one signal entered distribution.
    assert len(received_signals) == 1
    assert received_signals[0] is signal

    # Exactly three users received that one signal.
    assert len(delivery.deliveries) == 3

    delivered_user_ids = {
        user_id
        for user_id, delivered_signal in delivery.deliveries
    }

    assert delivered_user_ids == {
        101,
        202,
        303,
    }

    # Every user received the exact same StrategyOutput.
    for _, delivered_signal in delivery.deliveries:
        assert delivered_signal is signal

    # Three successful deliveries generated three
    # distribution events.
    assert len(distributed_signals) == 3

    for distributed_signal in distributed_signals:
        assert distributed_signal is signal