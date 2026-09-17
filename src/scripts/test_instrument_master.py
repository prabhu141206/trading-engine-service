from broker.angel_one.instrument_master import (
    AngelOneInstrumentMaster,
)


def main() -> None:
    instrument_master = AngelOneInstrumentMaster()

    print("Loading Angel One instrument master...")

    instrument_master.load()

    symbols = {
        "RELIANCE",
        "TCS",
        "INFY",
    }

    tokens = instrument_master.get_tokens(symbols)

    print("\nResolved tokens:")

    for symbol, token in tokens.items():
        print(f"{symbol} -> {token}")


if __name__ == "__main__":
    main()