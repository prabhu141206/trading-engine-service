import requests


INSTRUMENT_MASTER_URL = (
    "https://margincalculator.angelbroking.com/"
    "OpenAPI_File/files/OpenAPIScripMaster.json"
)


class AngelOneInstrumentMaster:
    """
    Loads Angel One's instrument master and provides
    symbol-to-token lookup for NSE equities and indices.
    """

    def __init__(self) -> None:
        self._symbol_tokens: dict[str, str] = {}

    def load(self) -> None:
        response = requests.get(
            INSTRUMENT_MASTER_URL,
            timeout=30,
        )
        response.raise_for_status()

        instruments = response.json()

        self._symbol_tokens.clear()

        for instrument in instruments:
            if instrument.get("exch_seg") != "NSE":
                continue

            symbol = instrument.get("symbol", "")
            name = instrument.get("name", "")
            token = instrument.get("token")

            # NSE equity instruments
            if symbol.endswith("-EQ"):
                self._symbol_tokens[name] = token

            # NSE index instruments
            elif symbol in {"NIFTY", "BANKNIFTY", "FINNIFTY"}:
                self._symbol_tokens[symbol] = token

    def get_token(self, symbol: str) -> str:
        try:
            return self._symbol_tokens[symbol]
        except KeyError:
            raise ValueError(
                f"Instrument token not found for symbol: {symbol}"
            )

    def get_tokens(self, symbols: set[str]) -> dict[str, str]:
        return {
            symbol: self.get_token(symbol)
            for symbol in symbols
        }

    def get_symbol(self, token: str) -> str:
        for symbol, stored_token in self._symbol_tokens.items():
            if stored_token == token:
                return symbol

        raise ValueError(
            f"Symbol not found for instrument token: {token}"
        )