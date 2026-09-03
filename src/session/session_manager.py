from event_system.event import Event
from event_system.event_bus import EventBus
from event_system.event_type import EventType


from session.user_session import UserSession
from registry.subscription_registry import SubscriptionRegistry
from registry.strategy_registry import StrategyRegistry
from registry.strategy_user_registry import StrategyUserRegistry
from db.user_session_repository import UserSessionRepository

class SessionManager:
    """
    Manage runtime user sessions.

    Responsibilities
    ----------------
    - Listen to market lifecycle events.
    - Load active users when market opens.
    - Create in-memory runtime sessions.
    - Populate SubscriptionRegistry.
    - Populate StrategyRegistry.
    - Clear sessions when market closes.
    """

    def __init__(
        self,
        event_bus: EventBus,
        subscription_registry: SubscriptionRegistry,
        strategy_registry: StrategyRegistry,
        strategy_user_registry: StrategyUserRegistry,
        user_session_repository: UserSessionRepository,
    ) -> None:

        # Dependency injection
        self._event_bus = event_bus
        self._subscription_registry = subscription_registry
        self._strategy_registry = strategy_registry
        self._strategy_user_registry = strategy_user_registry
        self._user_session_repository = user_session_repository

        # Active runtime sessions.
        self._sessions: dict[int, UserSession] = {}

    # ---------------------------------------------------------
    # Temporary data source
    # ---------------------------------------------------------

    def _load_active_users(self) -> list[UserSession]:
        """
        Load active user sessions from persistent storage.

        The repository handles database access and converts
        database configuration into UserSession objects.
        """

        return self._user_session_repository.get_active_sessions()

    # ---------------------------------------------------------
    # Session lifecycle
    # ---------------------------------------------------------

    def _create_user_sessions(self) -> None:
        """
        Create runtime sessions and register their
        market-data and strategy requirements.
        """

        active_sessions = self._load_active_users()

        for session in active_sessions:

            # Store runtime user session.
            self._sessions[session.user_id] = session

            # Register required market-data symbols.
            for symbol in session.subscribed_symbols:
                self._subscription_registry.add_symbol(symbol)

            # Register unique strategy groups.
            for strategy in session.strategies:
                self._strategy_registry.add_group(strategy)

                self._strategy_user_registry.subscribe(
                    user_id=session.user_id,
                    group=strategy,
                )


    def _clear_user_sessions(self) -> None:
        """
        Remove all runtime sessions and registry state.
        """
        self._sessions.clear()

        self._subscription_registry.clear()
        self._strategy_registry.clear()
        self._strategy_user_registry.clear()

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