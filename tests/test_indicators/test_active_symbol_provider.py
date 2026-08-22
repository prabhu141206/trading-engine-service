from indicators.fake_active_symbol_provider import (
    FakeActiveSymbolProvider,
)


def test_returns_active_symbols():

    provider = FakeActiveSymbolProvider(
        [
            "NIFTY",
            "BANKNIFTY",
            "RELIANCE",
        ]
    )

    symbols = provider.get_active_symbols()

    assert symbols == [
        "NIFTY",
        "BANKNIFTY",
        "RELIANCE",
    ]


def test_returns_copy_of_symbols():

    provider = FakeActiveSymbolProvider(
        ["NIFTY", "BANKNIFTY"]
    )

    symbols = provider.get_active_symbols()

    symbols.append("RELIANCE")

    assert provider.get_active_symbols() == [
        "NIFTY",
        "BANKNIFTY",
    ]


def test_empty_symbol_list():

    provider = FakeActiveSymbolProvider([])

    assert provider.get_active_symbols() == []