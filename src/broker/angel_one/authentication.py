import pyotp
from SmartApi import SmartConnect

from config.settings import settings
from dataclasses import dataclass

@dataclass(frozen=True)
class AngelOneSession:
    auth_token: str
    feed_token: str



class AngelOneAuthenticator:
    """
    Handles authentication with Angel One.

    Responsible only for creating an authenticated
    SmartConnect session and obtaining the feed token.
    """

    def __init__(self) -> None:
        self._smart_api = SmartConnect(
            api_key=settings.angel_api_key
        )

    def login(self) -> AngelOneSession:
        """
        Authenticate with Angel One and return the
        credentials required for the session.
        """

        totp = pyotp.TOTP(
            settings.angel_totp_secret
        ).now()

        response = self._smart_api.generateSession(
            settings.angel_client_code,
            settings.angel_pin,
            totp,
        )

        if not response.get("status"):
            raise RuntimeError(
                f"Angel One authentication failed: {response}"
            )

        auth_token = response["data"]["jwtToken"]
        feed_token = self._smart_api.getfeedToken()

        return AngelOneSession(
            auth_token=auth_token,
            feed_token=feed_token,
        )


    def get_api_key(self) -> str:
        return settings.angel_api_key

    def get_client_code(self) -> str:
        return settings.angel_client_code
    
    
    
    def get_feed_token(self) -> str:
        """
        Return the WebSocket feed token for the
        authenticated session.
        """

        return self._smart_api.getfeedToken()

    def get_smart_api(self) -> SmartConnect:
        """
        Return the SmartConnect client used by this authenticator.
        """
        return self._smart_api