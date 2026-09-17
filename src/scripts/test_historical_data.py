from datetime import datetime, timedelta

import pyotp
from SmartApi import SmartConnect

from config.settings import settings
from broker.angel_one.instrument_master import (
    AngelOneInstrumentMaster,
)


def main() -> None:
    # ---------------------------------------------------------
    # 1. Login to Angel One
    # ---------------------------------------------------------
    smart_api = SmartConnect(settings.angel_api_key)

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
            f"Angel One login failed: {login_response}"
        )

    print("Angel One login successful.")

    # ---------------------------------------------------------
    # 2. Load instrument master
    # ---------------------------------------------------------
    instrument_master = AngelOneInstrumentMaster()
    instrument_master.load()

    symbol = "RELIANCE"

    token = instrument_master.get_token(symbol)

    print(f"{symbol} -> token {token}")

    # ---------------------------------------------------------
    # 3. Request historical candles
    # ---------------------------------------------------------
    todate = datetime.now()
    fromdate = todate - timedelta(days=5)

    historic_params = {
        "exchange": "NSE",
        "symboltoken": token,
        "interval": "FIVE_MINUTE",
        "fromdate": fromdate.strftime("%Y-%m-%d %H:%M"),
        "todate": todate.strftime("%Y-%m-%d %H:%M"),
    }

    print("\nRequesting historical candles...")
    print(historic_params)

    response = smart_api.getCandleData(historic_params)

    if not response.get("status"):
        raise RuntimeError(
            f"Historical data request failed: {response}"
        )

    candles = response.get("data", [])

    print(f"\nReceived {len(candles)} candles.")

    # ---------------------------------------------------------
    # 4. Display the latest candles
    # ---------------------------------------------------------
    for candle in candles[-5:]:
        print(candle)


if __name__ == "__main__":
    main()