from event_system.event import Event
from event_system.event_type import EventType


class SystemMonitor:
    """
    Central observability component for the trading engine.

    This component only records and exposes monitoring state.
    It does not control any runtime component.
    """

    def __init__(self, event_bus):
        self._event_bus = event_bus

        self._system = {}
        self._market_data = {}
        self._candles = {}
        self._indicators = {}
        self._strategies = {}
        self._signal_distribution = {}
        self._health = {}

        self._event_bus.subscribe(
            EventType.MARKET_OPEN,
            self._on_market_open,
        )

        self._event_bus.subscribe(
            EventType.MARKET_CLOSE,
            self._on_market_close,
        )

        self._event_bus.subscribe(
            EventType.CANDLE_BATCH_CLOSED,
            self._on_candle_batch_closed,
        )

        self._event_bus.subscribe(
            EventType.INDICATOR_BATCH_UPDATED,
            self._on_indicator_batch_updated,
        )

        self._event_bus.subscribe(
            EventType.STRATEGY_SIGNAL_GENERATED,
            self._on_strategy_signal_generated,
        )

        self._event_bus.subscribe(
            EventType.SIGNAL_RECEIVED,
            self._on_signal_received,
        )

        self._event_bus.subscribe(
            EventType.SIGNAL_DISTRIBUTED,
            self._on_signal_distributed,
        )

    def _on_candle_batch_closed(self, event: Event) -> None:
        batch = event.payload

        for symbol in batch.candles:
            self.record_candle(
                symbol=symbol,
                timeframe=batch.timeframe,
            )

    def _on_indicator_batch_updated(
        self,
        event: Event,
    ) -> None:
        batch = event.payload

        symbols_count = len(batch.indicators)

        key = batch.timeframe

        self._indicators[key] = symbols_count

    def _on_strategy_signal_generated(
        self,
        event: Event,
    ) -> None:
        output = event.payload

        strategy_name = output.strategy_group.name

        current = self._strategies.get(
            strategy_name,
            {
                "signals": 0,
                "status": "HEALTHY",
            },
        )

        current["signals"] += 1

        self._strategies[strategy_name] = current


    def _on_signal_received(self, event):
        self._signal_distribution["signals_received"] = (
            self._signal_distribution.get("signals_received", 0) + 1
        )


    def _on_signal_distributed(self, event):
        self._signal_distribution["signals_distributed"] = (
            self._signal_distribution.get("signals_distributed", 0) + 1
        )


    def _on_strategy_signal_generated(
        self,
        event: Event,
    ) -> None:
        output = event.payload

        strategy_name = output.strategy_group.strategy_type

        current = self._strategies.get(
            strategy_name,
            {
                "signals": 0,
                "status": "HEALTHY",
            },
        )

        current["signals"] += 1

        self._strategies[strategy_name] = current

    def update_overall_status(self, status: str):
        self._system["overall_status"] = status

    def update_market_state(self, state: str):
        self._system["market_state"] = state

    def update_websocket_status(self, status: str):
        self._system["websocket"] = status

    def update_active_symbols(self, count: int):
        self._market_data["active_symbols"] = count

    def record_tick(self):
        self._market_data["ticks_received"] = (
            self._market_data.get("ticks_received", 0) + 1
        )

    def record_candle(
        self,
        symbol: str,
        timeframe: str,
    ):
        key = (symbol, timeframe)

        self._candles[key] = (
            self._candles.get(key, 0) + 1
        )
        
    def _on_market_open(self, event):
        self.update_market_state("OPEN")

    def _on_market_close(self, event):
        self.update_market_state("CLOSED")

    def get_snapshot(self) -> dict:
        return {
            "system": self._system.copy(),
            "market_data": self._market_data.copy(),
            "candles": self._candles.copy(),
            "indicators": self._indicators.copy(),
            "strategies": self._strategies.copy(),
            "signal_distribution": self._signal_distribution.copy(),
            "health": self._health.copy(),
        }