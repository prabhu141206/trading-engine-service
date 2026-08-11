from dataclasses import dataclass


@dataclass
class UserSession:
    user_id: int
    subscribed_symbols: set[str]