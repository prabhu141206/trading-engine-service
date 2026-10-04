import pyotp

from SmartApi.smartConnect import SmartConnect

from config.settings import settings


smart_api = SmartConnect(
    settings.angel_api_key
)

totp = pyotp.TOTP(
    settings.angel_totp_secret
).now()

response = smart_api.generateSession(
    settings.angel_client_code,
    settings.angel_pin,
    totp,
)

print(response)