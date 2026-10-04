import pyotp
from SmartApi import SmartConnect

from config.settings import settings

from broker.angel_one.instrument_master import (
    AngelOneInstrumentMaster,
)

from broker.angel_one.historical_data import (
    AngelOneHistoricalDataProvider,
)


def main() -> None:

    # Login
    smart_api = SmartConnect(
        settings.angel_api_key
    )

    totp = pyotp.TOTP(
        settings.angel_totp_secret
    ).now()

    login_response = smart_api.generateSession(
        settings.angel_client_code,
        settings.angel_pin,
        totp,
    )

    if not login_response.get("status"):
        raise RuntimeError(
            f"Login failed: {login_response}"
        )

    print("Login successful.")

    # Load instrument master
    instrument_master = AngelOneInstrumentMaster()
    instrument_master.load()

    # Create provider
    provider = AngelOneHistoricalDataProvider(
        smart_api=smart_api,
        instrument_master=instrument_master,
    )

    # Fetch 50 candles
    candles = provider.get_historical_candles(
        symbol="RELIANCE",
        timeframe="FIVE_MINUTE",
        count=50,
    )

    print(f"\nReceived {len(candles)} candles.")

    for candle in candles[-5:]:
        print(candle)


if __name__ == "__main__":
    main()