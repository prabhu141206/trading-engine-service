from event_system.event import Event
from event_system.event_bus import EventBus
from event_system.event_type import EventType

from session.user_session import UserSession

class SessionManager:

    def __init__(
        self,
        event_bus: EventBus,
    ) -> None:

        self._event_bus = event_bus

        # Active user sessions
        self._sessions: dict[int, UserSession] = {}

    # make a fake user loader
    def _load_active_users(self) -> list[UserSession]:
        """
        Temporary in-memory data source.
    
        Future implementation:
            - Query active users from database.
            - Query active symbol subscriptions for each user.
            - Build UserSession objects from persistent data.
        """
    
        return [
            UserSession(
                user_id=101,
                subscribed_symbols={"NIFTY", "BANKNIFTY"}
            ),
            UserSession(
                user_id=202,
                subscribed_symbols={"NIFTY"}
            ),
            UserSession(
                user_id=303,
                subscribed_symbols={"FINNIFTY"}
            ),
        ]


    def _create_session(
        self,
        user_id: int
    ) -> None:

        session = UserSession(
            user_id=user_id
        )

        self._sessions[user_id] = session



    def start(self) -> None:


        self._event_bus.subscribe(
            EventType.MARKET_OPEN,
            self._on_market_open
        )

        self._event_bus.subscribe(
            EventType.MARKET_CLOSE,
            self._on_market_close
        )

      


    # Event handlers (event publish by the event bus to this methods)
    def _on_market_open(
        self,
        event: Event
    ) -> None:

        user_ids = self._load_active_users()

        for user_id in user_ids:
            self._create_session(user_id)


    def _on_market_close(
        self,
        event: Event
    ) -> None:

        self._sessions.clear()
