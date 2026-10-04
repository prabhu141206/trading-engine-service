from broker.angel_one.authentication import AngelOneAuthenticator
from broker.angel_one.instrument_master import AngelOneInstrumentMaster
from broker.angel_one.websocket import AngelOneWebSocketClient


from market_data.models import Tick

def main() -> None:
    print("1. Starting...")

    print("2. Loading instrument master...")
    instrument_master = AngelOneInstrumentMaster()
    instrument_master.load()
    print("3. Instrument master loaded")

    print("4. Creating authenticator...")
    authenticator = AngelOneAuthenticator()
    print("5. Authenticator created")

    print("6. Creating WebSocket client...")
    websocket_client = AngelOneWebSocketClient(
        authenticator=authenticator,
        instrument_master=instrument_master,
    )
    print("7. WebSocket client created")

    def on_tick(tick: Tick) -> None:
        print(f"APPLICATION RECEIVED: {tick}")

    websocket_client.set_tick_handler(on_tick)

    print("8. Connecting...")
    websocket_client.connect()

    input("9. WebSocket is running. Press Enter to stop...\n")

    websocket_client.disconnect()
    print("10. Disconnected")


if __name__ == "__main__":
    main()