from dataclasses import dataclass
from datetime import datetime

from candle.candle_models import Candle, CandleBatch
from indicators.indicator_models import (
    IndicatorBatch,
    SymbolIndicatorState,
)

from .strategy_context import StrategyContext

@dataclass(frozen=True)
class CorrelationKey:
    """
    Identifies one exact symbol and market interval.
    """

    symbol: str
    timeframe: str
    start_time: datetime
    end_time: datetime


class StrategyCorrelator:
    """
    Correlates candle and indicator data belonging to the same
    symbol and market interval.

    The correlator does not:
        - route strategies
        - execute strategy logic
        - publish events
        - manage users
        - process ticks
    """

    def __init__(self) -> None:
        self._candles: dict[CorrelationKey, Candle] = {}
        self._indicators: dict[
            CorrelationKey,
            SymbolIndicatorState,
        ] = {}

    def process_candle_batch(
        self,
        batch: CandleBatch,
    ) -> list[StrategyContext]:
        """
        Store candle data and return any contexts that become complete.
        """
        contexts: list[StrategyContext] = []

        for symbol, candle in batch.candles.items():

            key = CorrelationKey(
                symbol=symbol,
                timeframe=batch.timeframe,
                start_time=batch.start_time,
                end_time=batch.end_time,
            )

            self._candles[key] = candle

            context = self._try_build_context(key)

            if context is not None:
                contexts.append(context)

        return contexts

    def process_indicator_batch(
        self,
        batch: IndicatorBatch,
    ) -> list[StrategyContext]:
        """
        Store indicator data and return any contexts that become complete.
        """
        contexts: list[StrategyContext] = []

        for symbol, indicator in batch.indicators.items():

            key = CorrelationKey(
                symbol=symbol,
                timeframe=batch.timeframe,
                start_time=batch.start_time,
                end_time=batch.end_time,
            )

            self._indicators[key] = indicator

            context = self._try_build_context(key)

            if context is not None:
                contexts.append(context)

        return contexts

    def _try_build_context(
        self,
        key: CorrelationKey,
    ) -> StrategyContext | None:
        """
        Build a StrategyContext only when both candle and indicator
        data for the exact same interval are available.
        """
        candle = self._candles.get(key)
        indicator = self._indicators.get(key)

        if candle is None or indicator is None:
            return None

        return StrategyContext(
            symbol=key.symbol,
            timeframe=key.timeframe,
            start_time=key.start_time,
            end_time=key.end_time,
            candle=candle,
            indicators={
                "EMA_10": indicator.ema_10,
            },
        )