from event_system.event import Event
from event_system.event_bus import EventBus
from event_system.event_type import EventType

from session.user_session import UserSession
from subscription_registry.subscription_registry import SubscriptionRegistry


class SessionManager:
    """
    Manage runtime user sessions.

    Responsibilities
    ----------------
    - Listen to market lifecycle events.
    - Load active users when market opens.
    - Create in-memory runtime sessions.
    - Populate SubscriptionRegistry.
    - Clear sessions when market closes.
    """

    def __init__(
        self,
        event_bus: EventBus,
        subscription_registry: SubscriptionRegistry,
    ) -> None:

        # Dependency injection
        self._event_bus = event_bus
        self._subscription_registry = subscription_registry

        # Active runtime sessions.
        self._sessions: dict[int, UserSession] = {}

    # ---------------------------------------------------------
    # Temporary data source
    # ---------------------------------------------------------

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

    # ---------------------------------------------------------
    # Session lifecycle
    # ---------------------------------------------------------

    def _create_user_sessions(self) -> None:
        """
        Create runtime sessions and register subscriptions.
        """

        active_sessions = self._load_active_users()

        for session in active_sessions:

            """
            Example:
            self._sessions[101] = session

            {
                101: UserSession(
                    user_id=101,
                    subscribed_symbols={"NIFTY", "BANKNIFTY"}
                )
            }
            """
            # Store runtime session.
            self._sessions[session.user_id] = session

            # Register symbol subscriptions.
            self._subscription_registry.add_session(session)

    def _clear_user_sessions(self) -> None:
        """
        Remove all runtime sessions and subscription mappings.
        """

        for session in self._sessions.values():
            self._subscription_registry.remove_session(session.user_id)

        self._sessions.clear()

    # ---------------------------------------------------------
    # Event registration
    # ---------------------------------------------------------

    def start(self) -> None:
        """
        Register market lifecycle event handlers.
        """

        self._event_bus.subscribe(
            EventType.MARKET_OPEN,
            self._on_market_open
        )

        self._event_bus.subscribe(
            EventType.MARKET_CLOSE,
            self._on_market_close
        )

    # ---------------------------------------------------------
    # Event handlers
    # ---------------------------------------------------------

    def _on_market_open(
        self,
        event: Event
    ) -> None:
        """
        Handle MARKET_OPEN event.
        """

        self._create_user_sessions()

    def _on_market_close(
        self,
        event: Event
    ) -> None:
        """
        Handle MARKET_CLOSE event.
        """

        self._clear_user_sessions()
