from market_session.market_state import MarketState


def test_market_state_values():
    assert MarketState.OPEN.value == "OPEN"
    assert MarketState.CLOSED.value == "CLOSED"