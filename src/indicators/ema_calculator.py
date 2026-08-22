class EMACalculator:
    """
    Calculates EMA values.

    This class contains only EMA calculation logic.
    It has no knowledge of EventBus, symbols,
    subscriptions, or strategy execution.
    """

    def __init__(
        self,
        period: int,
    ) -> None:

        if period <= 0:
            raise ValueError(
                "EMA period must be greater than zero."
            )

        self._period = period

        self._alpha = (
            2 / (period + 1)
        )

    def calculate_from_closes(
        self,
        closes: list[float],
    ) -> float:

        if not closes:
            raise ValueError(
                "At least one close price is required."
            )

        ema = closes[0]

        for close in closes[1:]:
            ema = self.update(
                previous_ema=ema,
                close=close,
            )

        return ema

    def update(
        self,
        previous_ema: float,
        close: float,
    ) -> float:

        return (
            close * self._alpha
            + previous_ema * (1 - self._alpha)
        )